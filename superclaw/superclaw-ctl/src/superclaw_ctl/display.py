from __future__ import annotations
from collections.abc import Mapping
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from superclaw_ctl.models import format_size

console = Console()
error_console = Console(stderr=True)

def print_status_table(containers: list) -> None:
    """Print a rich table of container statuses."""
    table = _table("Service", "State", "Health", "Ports", ("Image", {"overflow": "fold"}))
    for container in containers:
        table.add_row(
            str(_read(container, "service", "name", "Service", "Name", default="—")),
            _style_state(str(_read(container, "state", "State", default="unknown"))),
            _style_health(str(_read(container, "health", "Health", default="—"))),
            _format_ports(_read(container, "ports", "Ports", default="")),
            str(_read(container, "image", "Image", default="—")),
        )
    console.print(table)

def print_connection_info(host: str, ports: dict[str, int], token_hint: str) -> None:
    """Print connection panel with IP, ports, and redacted token."""
    primary_port = (
        ports.get("vLLM Model Router")
        or ports.get("vLLM Chat")
        or ports.get("vLLM Embed")
        or next(iter(ports.values()), 0)
    )
    url = f"http://{host}:{primary_port}" if primary_port else f"http://{host}"
    lines = [f"[bold]URL:[/bold] {url}"]
    lines.extend(f"{service}: {host}:{port}" for service, port in sorted(ports.items()))
    lines.append(f"[cyan]Token:[/cyan] {redact_token(token_hint)}")
    console.print(Panel.fit("\n".join(lines), title="Connection", border_style="blue"))

def print_check_results(results: list) -> None:
    """Print doctor check results with PASS/WARN/FAIL coloring."""
    table = _table("Check", "Result", ("Details", {"overflow": "fold"}), box_style=box.SIMPLE)
    labels = {"PASS": "[green]✓ PASS[/green]", "WARN": "[yellow]⚠ WARN[/yellow]", "FAIL": "[red]✗ FAIL[/red]"}
    for result in results:
        status = str(_read(result, "status", "result", default="unknown")).upper()
        table.add_row(
            str(_read(result, "name", "check", default="—")),
            labels.get(status, status),
            str(_read(result, "message", "detail", "details", default="")),
        )
    console.print(table)

def print_models_table(models: list) -> None:
    """Print table of available models."""
    table = _table("Name", ("Size", {"justify": "right"}), "Architecture", "Quantization", ("Context Length", {"justify": "right"}))
    for model in models:
        table.add_row(
            str(_read(model, "name", default="—")),
            format_size(int(_read(model, "size_bytes", default=0) or 0)),
            str(_read(model, "architecture", default="—") or "—"),
            str(_read(model, "quantization", default="—") or "—"),
            str(_read(model, "context_length", default="—") or "—"),
        )
    console.print(table)

def print_model_detail(model) -> None:
    """Print detailed model info panel."""
    rows = (
        ("Name", _read(model, "name", default="—")),
        ("Path", _read(model, "path", default="—")),
        ("Size", format_size(int(_read(model, "size_bytes", default=0) or 0))),
        ("Architecture", _read(model, "architecture", default="—") or "—"),
        ("Parameters", _read(model, "num_parameters", default="—") or "—"),
        ("Quantization", _read(model, "quantization", default="—") or "—"),
        ("Context Length", _read(model, "context_length", default="—") or "—"),
        ("Vocab Size", _read(model, "vocab_size", default="—") or "—"),
        ("Model Type", _read(model, "model_type", default="—") or "—"),
    )
    console.print(Panel.fit("\n".join(f"{label}: {value}" for label, value in rows), title="Model Details", border_style="cyan"))

def print_gpu_info(gpus: list) -> None:
    """Print GPU information table."""
    table = _table("Name", "Vendor", "Memory", "Driver", "Status")
    for gpu in gpus:
        table.add_row(
            str(_read(gpu, "name", default="—")),
            str(_read(gpu, "vendor", default="—")),
            str(_read(gpu, "memory", "memory_total", default="—")),
            str(_read(gpu, "driver", "driver_version", default="—")),
            str(_read(gpu, "status", "state", default="—")),
        )
    console.print(table)

def print_keys(secrets, *, reveal: bool = False) -> None:
    """Print keys, redacted unless reveal=True."""
    table = _table("Key", ("Value", {"overflow": "fold"}), box_style=box.SIMPLE)
    for key, value in sorted(_as_dict(secrets).items()):
        table.add_row(str(key), str(value if reveal or not isinstance(value, str) else redact_token(value)))
    console.print(table)

def print_config(config, secrets) -> None:
    """Print effective config with secrets redacted."""
    table = _table("Section", "Key", ("Value", {"overflow": "fold"}), box_style=box.SIMPLE)
    for key, value in _flatten(_as_dict(config)):
        table.add_row("config", key, _stringify(value))
    for key, value in _flatten(_as_dict(secrets)):
        table.add_row("secret", key, redact_token(str(value)))
    console.print(table)

def redact_token(token: str) -> str:
    """Show first 4 chars + '...' for display."""
    return "***" if len(token) <= 4 else token[:4] + "..."

def print_init_plan(
    models_dir: str,
    models: list,
    disk_check,
    images: list[str],
    image_size_bytes_approx: int,
    config_dir: str,
    *,
    models_dir_will_be_created: bool = False,
    model_statuses: dict[str, str] | None = None,
    model_bytes: dict[str, int] | None = None,
    image_present: bool = False,
    skip_models: bool = False,
) -> None:
    """Print a pre-flight summary of what init will do, before asking for confirmation.

    model_statuses maps model id -> "present" | "incomplete" | "missing" | "skipped".
    model_bytes maps model id -> estimated bytes to actually download:
      - For incomplete models this is the remaining bytes (snapshot_download is
        incremental — it SHA-checks each file and only fetches what's missing).
      - For missing models this is the full size_bytes_approx.
    disk_check may be None when no downloads are needed at all.
    """
    lines: list[str] = []
    dir_note = " [dim](will be created)[/dim]" if models_dir_will_be_created else ""

    # Models section
    lines.append("[bold]Models:[/bold]")
    for model in models:
        model_id = str(_read(model, "id", default=""))
        name = str(_read(model, "name", default="—"))
        role = str(_read(model, "role", default=""))
        size = int(_read(model, "size_bytes_approx", default=0) or 0)
        size_str = format_size(size) if size else "size unknown"
        role_label = f" [{role}]" if role else ""
        status = (model_statuses or {}).get(model_id, "missing")
        bytes_to_dl = (model_bytes or {}).get(model_id, size)
        bytes_str = format_size(bytes_to_dl) if bytes_to_dl else "size unknown"

        if status == "present":
            lines.append(f"  [green]✓[/green] {name}{role_label}  already present — will verify  →  {models_dir}")
        elif status == "incomplete":
            # snapshot_download is incremental: only missing/changed files are fetched
            remaining_note = f"up to ~{bytes_str} remaining" if bytes_to_dl else "some files missing"
            lines.append(f"  [yellow]⚠[/yellow] {name}{role_label}  incomplete — resuming sync ({remaining_note})  →  {models_dir}{dir_note}")
        elif status == "skipped":
            lines.append(f"  [dim]-[/dim] {name}{role_label}  skipped (--skip-models) — download/verify bypassed  →  {models_dir}{dir_note}")
        else:
            lines.append(f"  [cyan]↓[/cyan] {name}{role_label}  will download ~{size_str}  →  {models_dir}{dir_note}")

    # Docker images section
    lines.append("")
    lines.append("[bold]Docker images:[/bold]")
    for image in images:
        if image_present:
            lines.append(f"  [green]✓[/green] {image}  present locally — init will still run pull to check updates")
        else:
            lines.append(f"  [cyan]↓[/cyan] {image}  will pull ~{format_size(image_size_bytes_approx)}")

    # Disk space section
    lines.append("")
    if disk_check is not None:
        disk_status = str(_read(disk_check, "status", default="unknown")).lower()
        disk_msg = str(_read(disk_check, "message", default=""))
        disk_color = "green" if disk_status == "pass" else "yellow" if disk_status == "warn" else "red"
        lines.append(f"[bold]Disk space:[/bold] [{disk_color}]{disk_msg}[/{disk_color}]")
    else:
        if skip_models:
            lines.append("[bold]Disk space:[/bold] [yellow]Model download skipped; disk check not required for models[/yellow]")
        else:
            lines.append("[bold]Disk space:[/bold] [green]No download needed — all assets already present[/green]")

    # Config section
    lines.append("")
    lines.append(f"[bold]Config & keys:[/bold] will be written to {config_dir}")

    console.print(Panel.fit("\n".join(lines), title="Init Setup Plan", border_style="cyan"))

def print_error(message: str, *, hint: str = "") -> None:
    """Print an error panel to stderr with optional hint."""
    lines = [message]
    if hint:
        lines.append(f"Hint: {hint}")
    error_console.print(Panel.fit("\n".join(lines), title="Error", border_style="red"))

def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")

def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")

def _table(*columns: str | tuple[str, dict[str, Any]], box_style=box.SIMPLE_HEAD) -> Table:
    table = Table(box=box_style)
    for column in columns:
        table.add_column(column[0], **column[1]) if isinstance(column, tuple) else table.add_column(column)
    return table

def _read(item: Any, *keys: str, default: Any = "") -> Any:
    if isinstance(item, Mapping):
        for key in keys:
            if key in item:
                return item[key]
        return default
    for key in keys:
        if hasattr(item, key):
            return getattr(item, key)
    return default

def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    return {key: item for key, item in vars(value).items() if not key.startswith("_")} if hasattr(value, "__dict__") else {}

def _flatten(data: Mapping[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        rows.extend(_flatten(value, full_key) if isinstance(value, Mapping) else [(full_key, value)])
    return rows

def _format_ports(ports: Any) -> str:
    if isinstance(ports, str):
        return ports or "—"
    if isinstance(ports, Mapping):
        return ", ".join(f"{key}:{value}" for key, value in ports.items()) or "—"
    if isinstance(ports, list):
        rendered: list[str] = []
        for entry in ports:
            if isinstance(entry, Mapping):
                published = entry.get("PublishedPort") or entry.get("published")
                target = entry.get("TargetPort") or entry.get("target")
                rendered.append(f"{published}->{target}" if published and target else str(published or ""))
            else:
                rendered.append(str(entry))
        return ", ".join(part for part in rendered if part) or "—"
    return "—"

def _style_state(state: str) -> str:
    lowered = state.lower()
    if lowered == "running":
        return f"[green]{state}[/green]"
    if lowered in {"exited", "dead", "failed"}:
        return f"[red]{state}[/red]"
    return f"[yellow]{state}[/yellow]" if lowered in {"starting", "created", "restarting"} else state

def _style_health(health: str) -> str:
    lowered = health.lower()
    if lowered == "healthy":
        return f"[green]{health}[/green]"
    if lowered in {"unhealthy", "failed"}:
        return f"[red]{health}[/red]"
    return f"[yellow]{health}[/yellow]" if lowered in {"starting", "unknown"} else (health or "—")

def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "null" if value is None else str(value)
