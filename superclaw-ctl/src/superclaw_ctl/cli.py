"""CLI entry point — thin Typer callbacks delegating to domain modules."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.panel import Panel

from superclaw_ctl import __version__
from superclaw_ctl.config import (
    Config,
    Secrets,
    config_exists,
    get_config_dir,
    load_config,
    load_secrets,
    save_config,
    save_secrets,
    secrets_exists,
    validate_secrets,
)
from superclaw_ctl.display import (
    console,
    print_check_results,
    print_config,
    print_connection_info,
    print_error,
    print_gpu_info,
    print_keys,
    print_model_detail,
    print_models_table,
    print_status_table,
    print_success,
    print_warning,
)
from superclaw_ctl.errors import SuperclawCtlError

app = typer.Typer(
    name="superclaw-ctl",
    help="Manage SuperClaw vLLM containers and model service.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)
models_app = typer.Typer(help="Model management commands.", no_args_is_help=True)
keys_app = typer.Typer(help="API key management.", no_args_is_help=True)
config_app = typer.Typer(help="Configuration management.", no_args_is_help=True)
clean_app = typer.Typer(help="Cleanup commands.", no_args_is_help=True)

app.add_typer(models_app, name="models")
app.add_typer(keys_app, name="keys")
app.add_typer(config_app, name="config")
app.add_typer(clean_app, name="clean")

Verbose = Annotated[bool, typer.Option("--verbose", "-v", help="Enable debug logging.")]

_LOCAL_NO_PROXY_TARGETS = ("localhost", "127.0.0.1")


def _handle_error(exc: SuperclawCtlError) -> None:
    print_error(exc.message, hint=exc.hint or "")
    raise typer.Exit(code=exc.exit_code)


def _get_adapter(config: Config | None = None, secrets: Secrets | None = None):
    from superclaw_ctl.docker import DockerAdapter

    redact = []
    if secrets:
        redact = [secrets.vllm_api_key]
    return DockerAdapter(secrets_to_redact=redact)


def _compose_env(
    config: Config,
    secrets: Secrets,
    *,
    backend_ready_timeout_seconds: int | None = None,
    router_port: int | None = None,
) -> dict[str, str]:
    env = {
        "VLLM_API_KEY": secrets.vllm_api_key,
        "VLLM_IMAGE": config.images.vllm,
        "LOCAL_MODELS_DIR": str(Path(config.paths.models_dir).expanduser()),
        "LOCAL_LOGS_DIR": str(Path(config.paths.logs_dir).expanduser()),
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "NO_PROXY": "",
    }
    if backend_ready_timeout_seconds is not None:
        env["VLLM_BACKEND_READY_TIMEOUT_SECONDS"] = str(backend_ready_timeout_seconds)
    if router_port is not None:
        env["ROUTER_PORT"] = str(router_port)
    return env


def _get_compose_project(
    config: Config,
    secrets: Secrets,
    *,
    backend_ready_timeout_seconds: int | None = None,
    router_port: int | None = None,
):
    from superclaw_ctl.compose import ComposeProject

    adapter = _get_adapter(config, secrets)
    compose_files = _resolve_compose_files(config)
    http_proxy, https_proxy, no_proxy = _read_proxy_env()
    env = _compose_env(
        config,
        secrets,
        backend_ready_timeout_seconds=backend_ready_timeout_seconds,
        router_port=router_port,
    )
    env["HTTP_PROXY"] = http_proxy
    env["HTTPS_PROXY"] = https_proxy
    env["NO_PROXY"] = no_proxy
    return ComposeProject(adapter, compose_files, project_name=config.compose.project_name, env=env)


def _read_proxy_env() -> tuple[str, str, str]:
    """Resolve proxy env vars using uppercase first, then lowercase."""
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy", "")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy", "")
    no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy", "")
    return http_proxy, https_proxy, no_proxy


def _missing_local_no_proxy_entries(no_proxy: str) -> list[str]:
    entries = {part.strip().lower() for part in no_proxy.split(",") if part.strip()}
    return [target for target in _LOCAL_NO_PROXY_TARGETS if target.lower() not in entries]


def _warn_if_proxy_missing_local_no_proxy() -> bool:
    """Warn if proxy is enabled but localhost bypass is missing."""
    http_proxy, https_proxy, no_proxy = _read_proxy_env()
    if not (http_proxy or https_proxy):
        return False

    missing = _missing_local_no_proxy_entries(no_proxy)
    if not missing:
        return False

    missing_csv = ",".join(missing)
    current = no_proxy or "<empty>"
    console.print(
        Panel.fit(
            "\n".join(
                [
                    "[bold yellow]Proxy configuration warning[/bold yellow]",
                    "Detected HTTP(S) proxy without a full local NO_PROXY bypass.",
                    "Local health checks can fail when localhost traffic is proxied.",
                    "",
                    f"Current NO_PROXY: {current}",
                    f"Add at least: {missing_csv}",
                    "Suggested: NO_PROXY=$NO_PROXY,localhost,127.0.0.1",
                ]
            ),
            border_style="yellow",
            title="Proxy Check",
        )
    )
    return True


def _resolve_compose_files(config: Config) -> list[Path]:
    compose_dir = Path(config.paths.compose_dir).expanduser()
    compose_files = [compose_dir / "docker-compose.vllm.yml"]
    for extra_file in config.compose.extra_files:
        extra_path = Path(extra_file).expanduser()
        if not extra_path.is_absolute():
            extra_path = compose_dir / extra_path
        compose_files.append(extra_path)
    return compose_files


def _get_host_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


_BANNER = r"""
       ▄██▄
     ▄█▓▓▓▓█▄
   ▄█▓▒▒▒▒▒▒▓█▄    │   ____                              ____ ___
  █▓▒░░░░░░░░▒▓█   │  / ___| _   _  _ __    ___  _ __   / ___|| |  __ _ __      __
   ▀█▓▒▒▒▒▒▒▓█▀    │  \___ \| | | || '_ \  / _ \| '__| | |    | | / _` |\ \ /\ / /
     ▀█▓▓▓▓█▀      │   ___) | |_| ||  _) ||  __/| |    | |___ | || (_| | \ V  V /
       ▀██▀        │  |____/ \__,_|| .__/  \___||_|     \____||_| \__,_|  \_/\_/
                                   |_|
"""


# ─── init ───────────────────────────────────────────────────────────────────

@app.command()
def init(
    models_dir: Annotated[str, typer.Option("--models-dir", help="Path to models directory.")] = "~/.models",
    skip_models: Annotated[bool, typer.Option("--skip-models", help="Skip model download (offline use).")] = False,
    verbose: Verbose = False,
) -> None:
    """Initialize superclaw-ctl: check environment, generate keys, download models, save config."""
    from superclaw_ctl.checks import check_compose, check_docker, check_gpu_minimum_requirements
    from superclaw_ctl.gpu import check_gpu_access, detect_gpus
    from superclaw_ctl.secrets import generate_key

    adapter = _get_adapter()
    console.print(_BANNER, markup=False, highlight=False)

    # Check prerequisites
    console.print("\n[bold]Checking prerequisites...[/bold]")
    docker_check = check_docker(adapter)
    compose_check = check_compose(adapter)
    print_check_results([docker_check, compose_check])

    if docker_check.status == "fail":
        print_error(docker_check.message, hint=docker_check.hint)
        raise typer.Exit(1)
    if compose_check.status == "fail":
        print_error(compose_check.message, hint=compose_check.hint)
        raise typer.Exit(1)

    # GPU detection + minimum requirement check (hard fail before any network I/O)
    console.print("\n[bold]Detecting GPUs...[/bold]")
    gpus = detect_gpus()
    warnings = check_gpu_access()
    if gpus:
        print_gpu_info([{"name": g.name, "driver": g.driver_version, "status": f"{g.tiles} tiles"} for g in gpus])
    else:
        print_warning("No GPUs detected. vLLM may not work without GPU access.")
    for w in warnings:
        print_warning(w)

    gpu_min_check = check_gpu_minimum_requirements(gpus)
    print_check_results([gpu_min_check])
    if gpu_min_check.status == "fail":
        print_error(gpu_min_check.message, hint=gpu_min_check.hint)
        raise typer.Exit(1)

    # Pull image
    console.print(f"\n[bold]Pulling vLLM image...[/bold]")
    config = Config()
    try:
        adapter.passthrough(["pull", config.images.vllm])
    except SuperclawCtlError as exc:
        print_warning(f"Image pull failed: {exc.message}")
        print_warning("You can retry later with `superclaw-ctl pull`.")

    # Download models
    if not skip_models:
        console.print("\n[bold]Downloading models...[/bold]")
        from superclaw_ctl.download import download_model
        from superclaw_ctl.registry import load_registry

        registry = load_registry()
        models_path = Path(models_dir).expanduser()
        models_path.mkdir(parents=True, exist_ok=True)

        for entry in registry.get_active_models():
            result = download_model(
                entry,
                models_path,
                on_progress=lambda msg: console.print(f"  [dim]{msg}[/dim]"),
            )
            if result.error:
                if result.already_present:
                    print_warning(f"Model verification warning ({entry.name}): {result.error}")
                    print_warning(
                        "Local files are present but remote verification failed. "
                        "Check connectivity/proxy settings and re-run init later."
                    )
                else:
                    print_warning(f"Model download failed ({entry.name}): {result.error}")
                    print_warning("You can retry later or download manually.")
            elif result.already_present:
                print_success(f"{entry.name}: verified ✓")
            else:
                print_success(f"{entry.name}: downloaded to {result.local_dir}")
    else:
        console.print("\n[dim]Skipping model download (--skip-models).[/dim]")

    # Generate keys
    console.print("\n[bold]Generating API keys...[/bold]")
    secrets = Secrets(
        vllm_api_key=generate_key(),
    )
    console.print("[green]Keys generated.[/green] They will be shown once below:")
    print_keys(secrets, reveal=True)

    # Build config and extract bundled compose templates
    config = Config(
        paths=config.paths.model_copy(update={"models_dir": models_dir}),
    )
    _extract_templates(config)

    # Save
    save_config(config)
    save_secrets(secrets)
    print_success(f"Config saved to {get_config_dir()}")

    # Run doctor
    console.print("\n[bold]Running diagnostics...[/bold]")
    _run_doctor_checks(config, secrets, verbose)

    # Next steps (superclaw-ctl up)
    print_success("[bold green]Initialization complete![/bold green]")
    console.print(Panel.fit("\n".join([
        "Run [cyan]superclaw-ctl up[/cyan] to start containers and services.",
        "Run [cyan]superclaw-ctl --help[/cyan] for more commands and options.",
    ]), title="Next Steps", border_style="green"))


def _extract_templates(config: Config) -> None:
    """Copy bundled compose templates to compose_dir."""
    import importlib.resources

    compose_dir = Path(config.paths.compose_dir).expanduser()
    compose_dir.mkdir(parents=True, exist_ok=True)

    templates_pkg = importlib.resources.files("superclaw_ctl.templates")
    for template_name in ["docker-compose.vllm.yml"]:
        resource = templates_pkg.joinpath(template_name)
        content = resource.read_text(encoding="utf-8")
        (compose_dir / template_name).write_text(content, encoding="utf-8")
    print_success(f"Compose templates written to {compose_dir}")


# ─── up ─────────────────────────────────────────────────────────────────────

@app.command()
def up(
    router_port: Annotated[int, typer.Option(help="Router port exposed inside the vLLM container.")] = 8080,
    timeout: Annotated[int, typer.Option(help="Startup/readiness timeout in seconds for CLI probes and in-container backend waits (default 1200).")] = 1200,
    verbose: Verbose = False,
) -> None:
    """Start vLLM container (with vllm-router), then wait for health."""
    try:
        config = load_config()
        secrets = load_secrets()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return

    proxy_bypass_warning = _warn_if_proxy_missing_local_no_proxy()

    project = _get_compose_project(
        config,
        secrets,
        backend_ready_timeout_seconds=timeout,
        router_port=router_port,
    )
    services = ["vllm"]

    rendered = project.render_config()
    # Compare against the expanded path: _compose_env injects the expanded
    # LOCAL_MODELS_DIR, so a `~`-prefixed config value would never match the
    # rendered compose otherwise.
    configured_models_dir = str(Path(config.paths.models_dir).expanduser())
    if configured_models_dir not in rendered:
        print_error(
            "Compose config did not include the configured models directory.",
            hint=(
                f"Configured path: {configured_models_dir}\n"
                "Run `superclaw-ctl config show` and ensure paths.models_dir is correct for your host."
            ),
        )
        raise typer.Exit(1)
    if verbose:
        console.print(f"[dim]Using models directory from config: {configured_models_dir}[/dim]")

    console.print("[bold]Starting containers...[/bold]")
    try:
        # compose.up() streams output and blocks until depends_on: service_healthy
        # is satisfied (which can take ~5 min for vLLM to load its model).
        project.up(services=services)
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return

    # Wait for full runtime readiness (chat, embed, and router).
    from superclaw_ctl.health import wait_for_healthy

    console.print("[bold]Waiting for model backends to become healthy...[/bold]")

    chat_status = wait_for_healthy(
        "http://127.0.0.1:18103/v1/models",
        service_name="vLLM chat",
        headers={"Authorization": f"Bearer {secrets.vllm_api_key}"},
        timeout=timeout,
        on_retry=lambda attempt, elapsed: console.print(f"[dim]  Chat: attempt {attempt} ({elapsed:.0f}s elapsed)...[/dim]") if verbose else None,
    )

    embed_status = wait_for_healthy(
        "http://127.0.0.1:18104/v1/models",
        service_name="vLLM embed",
        headers={"Authorization": f"Bearer {secrets.vllm_api_key}"},
        timeout=timeout,
        on_retry=lambda attempt, elapsed: console.print(f"[dim]  Embed: attempt {attempt} ({elapsed:.0f}s elapsed)...[/dim]") if verbose else None,
    )

    if chat_status.healthy:
        print_success(f"vLLM chat healthy ({chat_status.latency_ms:.0f}ms)")
    else:
        print_warning(f"vLLM chat not ready: {chat_status.error}")
    if embed_status.healthy:
        print_success(f"vLLM embed healthy ({embed_status.latency_ms:.0f}ms)")
    else:
        print_warning(f"vLLM embed not ready: {embed_status.error}")
    if not chat_status.healthy or not embed_status.healthy:
        if proxy_bypass_warning:
            print_warning(
                "Proxy settings may be blocking local health probes. "
                "Ensure NO_PROXY includes localhost and 127.0.0.1."
            )
        print_error(
            "Model backends did not become healthy before timeout.",
            hint="Increase `superclaw-ctl up --timeout` and retry.",
        )
        raise typer.Exit(1)

    router_status = wait_for_healthy(
        f"http://127.0.0.1:{router_port}/v1/models",
        service_name="vLLM router",
        headers={"Authorization": f"Bearer {secrets.vllm_api_key}"},
        timeout=timeout,
        on_retry=lambda attempt, elapsed: console.print(f"[dim]  Router: attempt {attempt} ({elapsed:.0f}s elapsed)...[/dim]") if verbose else None,
    )
    if router_status.healthy:
        print_success(f"vLLM router healthy ({router_status.latency_ms:.0f}ms)")
    else:
        print_error(
            f"vLLM router not ready: {router_status.error}",
            hint=f"Check `superclaw-ctl logs` and verify --router-port {router_port}.",
        )
        raise typer.Exit(1)

    # Print connection info
    host_ip = _get_host_ip()
    ports = {
        "vLLM Model Router": router_port,
        "vLLM Chat": 18103,
        "vLLM Embed": 18104,
    }
    print_connection_info(host_ip, ports, secrets.vllm_api_key)
    if router_port != 8080:
        print_warning(f"Use --router-port {router_port} when running `superclaw-ctl status`.")


# ─── down ───────────────────────────────────────────────────────────────────

@app.command()
def down(verbose: Verbose = False) -> None:
    """Stop and remove containers."""
    try:
        config = load_config()
        secrets = load_secrets()
        project = _get_compose_project(config, secrets)
        console.print("[bold]Stopping containers...[/bold]")
        project.down()
        print_success("Containers stopped and removed.")
    except SuperclawCtlError as exc:
        _handle_error(exc)


# ─── restart ────────────────────────────────────────────────────────────────

@app.command()
def restart(
    service: Annotated[Optional[str], typer.Argument(help="Service to restart (vllm only).")] = None,
    verbose: Verbose = False,
) -> None:
    """Restart services."""
    try:
        config = load_config()
        secrets = load_secrets()
        project = _get_compose_project(config, secrets)
        if service and service != "vllm":
            print_error("Unknown service. Valid value: vllm")
            raise typer.Exit(1)
        services = ["vllm"]
        project.restart(services)
        print_success("Restarted vllm.")
    except SuperclawCtlError as exc:
        _handle_error(exc)


# ─── status ─────────────────────────────────────────────────────────────────

@app.command()
def status(
    router_port: Annotated[int, typer.Option(help="Router port exposed inside the vLLM container.")] = 8080,
    verbose: Verbose = False,
) -> None:
    """Show container states, health, and endpoints."""
    try:
        config = load_config()
        secrets = load_secrets()
        project = _get_compose_project(config, secrets)
        containers = project.ps()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return

    if not containers:
        other_projects = project.running_project_names()
        if other_projects:
            console.print(
                f"[yellow]No containers found for project {config.compose.project_name}; "
                f"other Compose projects are running: {', '.join(other_projects)}.[/yellow]"
            )
        else:
            console.print("[dim]No containers running.[/dim]")
        return

    print_status_table(containers)

    # GPU info
    from superclaw_ctl.gpu import detect_gpus, gpu_utilization

    util = gpu_utilization()
    if util:
        console.print(
            f"\n[bold]GPU Utilization:[/bold] (via xpu-smi, note that values may not be accurate)\n"
        )
        print_gpu_info(util)

    # Health probes
    from superclaw_ctl.health import check_vllm_health, check_router_health

    chat = check_vllm_health(api_key=secrets.vllm_api_key, port=18103)
    if chat.healthy:
        print_success(f"vLLM chat: healthy ({chat.latency_ms:.0f}ms)")
    else:
        print_warning(f"vLLM chat: {chat.error or 'unhealthy'}")

    embed = check_vllm_health(api_key=secrets.vllm_api_key, port=18104)
    if embed.healthy:
        print_success(f"vLLM embed: healthy ({embed.latency_ms:.0f}ms)")
    else:
        print_warning(f"vLLM embed: {embed.error or 'unhealthy'}")

    router = check_router_health(api_key=secrets.vllm_api_key, port=router_port)
    if router.healthy:
        print_success(f"Model service router: healthy ({router.latency_ms:.0f}ms)")
    else:
        print_warning(f"Model service router: {router.error or 'unhealthy'}")


# ─── logs ───────────────────────────────────────────────────────────────────

@app.command()
def logs(
    service: Annotated[Optional[str], typer.Argument(help="Service name (vllm only).")] = None,
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow log output.")] = False,
    tail: Annotated[int, typer.Option("--tail", help="Show the last N log lines before printing.")] = 200,
    verbose: Verbose = False,
) -> None:
    """Show or follow container logs."""
    try:
        config = load_config()
        secrets = load_secrets()
        project = _get_compose_project(config, secrets)
        if service and service != "vllm":
            print_error("Unknown service. Valid value: vllm")
            raise typer.Exit(1)
        result = project.logs("vllm", follow=follow, tail=tail)
        if isinstance(result, str):
            console.print(result)
        else:
            for line in result:
                console.print(line)
    except SuperclawCtlError as exc:
        _handle_error(exc)
    except KeyboardInterrupt:
        pass


# ─── pull ───────────────────────────────────────────────────────────────────

@app.command()
def pull(
    verbose: Verbose = False,
) -> None:
    """Pull/update vLLM image."""
    try:
        config = load_config()
        secrets = load_secrets()
        project = _get_compose_project(config, secrets)
        console.print("[bold]Pulling images...[/bold]")
        project.pull(services=["vllm"])
        print_success("Images pulled successfully.")
    except SuperclawCtlError as exc:
        _handle_error(exc)


# ─── doctor ─────────────────────────────────────────────────────────────────

@app.command()
def doctor(verbose: Verbose = False) -> None:
    """Run diagnostics without changing state."""
    try:
        config = load_config()
        secrets = load_secrets()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return

    _run_doctor_checks(config, secrets, verbose)


def _run_doctor_checks(config: Config, secrets: Secrets, verbose: bool) -> None:
    from superclaw_ctl.checks import check_compose, check_docker, check_image_available
    from superclaw_ctl.gpu import check_gpu_access
    from superclaw_ctl.models import list_models

    adapter = _get_adapter(config, secrets)
    results = [
        check_docker(adapter),
        check_compose(adapter),
        check_image_available(adapter, config.images.vllm),
    ]

    # GPU check
    gpu_warnings = check_gpu_access()
    if gpu_warnings:
        from superclaw_ctl.checks import CheckResult
        results.append(CheckResult(name="GPU access", status="warn", message="; ".join(gpu_warnings)))
    else:
        from superclaw_ctl.checks import CheckResult
        results.append(CheckResult(name="GPU access", status="pass", message="GPU devices accessible"))

    # Models dir
    from superclaw_ctl.checks import CheckResult
    models_path = Path(config.paths.models_dir).expanduser()
    if models_path.exists():
        models = list_models(models_path)
        results.append(CheckResult(
            name="Models directory",
            status="pass" if models else "warn",
            message=f"{len(models)} model(s) found" if models else "No models found",
        ))
    else:
        results.append(CheckResult(name="Models directory", status="warn", message=f"Not found: {models_path}"))

    # Secrets validation
    secret_warnings = validate_secrets(secrets)
    if secret_warnings:
        results.append(CheckResult(name="Secrets", status="warn", message="; ".join(secret_warnings)))
    else:
        results.append(CheckResult(name="Secrets", status="pass", message="All tokens valid"))

    print_check_results(results)


# ─── models ─────────────────────────────────────────────────────────────────

@models_app.command("list")
def models_list(verbose: Verbose = False) -> None:
    """List available models in the models directory."""
    try:
        config = load_config()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return

    from superclaw_ctl.models import list_models

    models_path = Path(config.paths.models_dir).expanduser()
    if not models_path.exists():
        print_error(f"Models directory not found: {models_path}")
        raise typer.Exit(1)

    models = list_models(models_path)
    if not models:
        console.print("[dim]No models found.[/dim]")
        return
    print_models_table(models)


@models_app.command("info")
def models_info(
    name: Annotated[str, typer.Argument(help="Model name (subdirectory in models_dir).")],
    verbose: Verbose = False,
) -> None:
    """Show detailed info for a specific model."""
    try:
        config = load_config()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return

    from superclaw_ctl.models import get_model_info

    info = get_model_info(Path(config.paths.models_dir).expanduser(), name)
    if info is None:
        print_error(f"Model not found: {name}")
        raise typer.Exit(1)
    print_model_detail(info)


# ─── keys ───────────────────────────────────────────────────────────────────

@keys_app.command("show")
def keys_show(
    reveal: Annotated[bool, typer.Option("--reveal", help="Show full key values.")] = False,
) -> None:
    """Show stored API keys (redacted by default)."""
    try:
        secrets = load_secrets()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return
    print_keys(secrets, reveal=reveal)


@keys_app.command("rotate")
def keys_rotate() -> None:
    """Generate new API keys and save them."""
    from superclaw_ctl.secrets import generate_key

    try:
        secrets = Secrets(
            vllm_api_key=generate_key(),
        )
        save_secrets(secrets)
        print_success("Keys rotated successfully.")
        print_warning("Restart containers with `superclaw-ctl down && superclaw-ctl up` to apply new keys.")
        print_keys(secrets, reveal=True)
    except SuperclawCtlError as exc:
        _handle_error(exc)


# ─── config ─────────────────────────────────────────────────────────────────

@config_app.command("show")
def config_show() -> None:
    """Show effective configuration (secrets redacted)."""
    try:
        config = load_config()
        secrets = load_secrets() if secrets_exists() else Secrets()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return
    print_config(config, secrets)


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Config key in dot notation (e.g., 'paths.models_dir').")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Update a config value."""
    try:
        config = load_config()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return

    parts = key.split(".")
    data = config.model_dump()
    target = data
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            print_error(f"Invalid config key: {key}")
            raise typer.Exit(1)
        target = target[part]

    if parts[-1] not in target:
        print_error(f"Unknown config key: {key}")
        raise typer.Exit(1)

    current_value = target[parts[-1]]
    if isinstance(current_value, str):
        parsed_value = value
    else:
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            expected_type = type(current_value).__name__
            print_error(f"Config key {key} expects {expected_type}; pass JSON (example: '[\"item\"]', 'true', '42').")
            raise typer.Exit(1)

    target[parts[-1]] = parsed_value
    try:
        updated = Config.model_validate(data)
        save_config(updated)
        print_success(f"Set {key} = {value}")
    except Exception as exc:
        print_error(f"Invalid value: {exc}")
        raise typer.Exit(1)


# ─── clean ──────────────────────────────────────────────────────────────────

@clean_app.command("containers")
def clean_containers(
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be removed.")] = False,
) -> None:
    """Stop and remove containers."""
    if dry_run:
        console.print("[bold]Would remove:[/bold]")
        console.print("  - All superclaw containers (docker compose down)")
        return
    if not force:
        typer.confirm("Remove all superclaw containers?", abort=True)
    try:
        config = load_config()
        secrets = load_secrets()
        project = _get_compose_project(config, secrets)
        project.down()
        print_success("Containers removed.")
    except SuperclawCtlError as exc:
        _handle_error(exc)


@clean_app.command("images")
def clean_images(
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be removed.")] = False,
) -> None:
    """Remove docker images."""
    try:
        config = load_config()
    except SuperclawCtlError as exc:
        _handle_error(exc)
        return

    images = [config.images.vllm]
    if dry_run:
        console.print("[bold]Would remove images:[/bold]")
        for img in images:
            console.print(f"  - {img}")
        return
    if not force:
        console.print("Will remove images:")
        for img in images:
            console.print(f"  - {img}")
        typer.confirm("Proceed?", abort=True)

    adapter = _get_adapter()
    for img in images:
        try:
            adapter.run(["rmi", img], timeout=30)
            print_success(f"Removed {img}")
        except SuperclawCtlError:
            print_warning(f"Could not remove {img} (may not exist)")


@clean_app.command("volumes")
def clean_volumes(
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be removed.")] = False,
) -> None:
    """Remove docker volumes."""
    volumes: list[str] = []
    if dry_run:
        console.print("[bold]Would remove volumes:[/bold]")
        if not volumes:
            console.print("  - No managed volumes")
        for vol in volumes:
            console.print(f"  - {vol}")
        return
    if not volumes:
        console.print("[dim]No managed volumes to remove.[/dim]")
        return
    if not force:
        typer.confirm("Remove all superclaw docker volumes? This deletes persistent data.", abort=True)

    adapter = _get_adapter()
    for vol in volumes:
        try:
            adapter.run(["volume", "rm", vol], timeout=30)
            print_success(f"Removed volume {vol}")
        except SuperclawCtlError:
            print_warning(f"Could not remove volume {vol} (may not exist)")


@clean_app.command("config")
def clean_config(
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be removed.")] = False,
) -> None:
    """Remove configuration directory."""
    config_dir = get_config_dir()
    if dry_run:
        console.print("[bold]Would remove:[/bold]")
        console.print(f"  - {config_dir}")
        return
    if not config_dir.exists():
        console.print("[dim]Config directory does not exist.[/dim]")
        return

    if not force:
        typer.confirm(f"Remove {config_dir} and all its contents?", abort=True)

    import shutil
    shutil.rmtree(config_dir)
    print_success(f"Removed {config_dir}")


@clean_app.command("all")
def clean_all(
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be removed.")] = False,
) -> None:
    """Remove containers, images, volumes, and config."""
    if dry_run:
        console.print("[bold]Would remove:[/bold]")
        console.print("  - All superclaw containers")
        console.print("  - Docker images (vLLM)")
        console.print("  - Docker volumes (none managed)")
        console.print(f"  - Config directory ({get_config_dir()})")
        console.print("  [dim]Note: The models directory (~/.models by default) is never deleted.[/dim]")
        return

    if not force:
        typer.confirm("Remove ALL superclaw resources (containers, images, volumes, config)?", abort=True)

    clean_containers(force=True)
    clean_images(force=True)
    clean_volumes(force=True)
    clean_config(force=True)


# ─── version ────────────────────────────────────────────────────────────────

@app.command()
def version() -> None:
    """Show version info for CLI, Docker, and Compose."""
    adapter = _get_adapter()
    console.print(f"[bold]superclaw-ctl[/bold] {__version__}")
    console.print(f"Docker:  {adapter.docker_version() or '[red]not found[/red]'}")
    console.print(f"Compose: {adapter.compose_version() or '[red]not found[/red]'}")
