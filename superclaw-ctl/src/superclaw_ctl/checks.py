from __future__ import annotations

"""Prerequisite environment checks for superclaw-ctl."""

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any, Literal, Protocol
import re
import socket

try:
    from .docker import DockerAdapter
except ImportError:  # pragma: no cover - docker.py may land later.
    class DockerAdapter(Protocol):
        def run(self, argv: Sequence[str], *, timeout: float | None = None) -> Any: ...

from .gpu import GPUInfo

_ARC_B70_PCI_ID = "E223"  # Intel® Arc™ Pro B70 Graphics (PCIe ID = 8086:E223)
_MIN_B70_COUNT = 4  # Minimum GPUs required (matches tensor_parallel_size in vllm_models.json)


@dataclass(slots=True)
class CheckResult:
    """Result of a single prerequisite check."""

    name: str
    status: Literal["pass", "warn", "fail"]
    message: str
    hint: str = ""


def _version_tuple(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)+)", text)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def _run_text(adapter: DockerAdapter, argv: list[str]) -> tuple[bool, str]:
    try:
        result = adapter.run(argv)
    except Exception as exc:
        return False, str(exc)
    code = getattr(result, "returncode", 0)
    stdout = getattr(result, "stdout", result)
    stderr = getattr(result, "stderr", "")
    text = "\n".join(part for part in (str(stdout).strip(), str(stderr).strip()) if part).strip()
    return code == 0, text


def _config_get(config: Any, dotted: str, default: Any = None) -> Any:
    value = config
    for part in dotted.split("."):
        if isinstance(value, dict):
            value = value.get(part, default)
        else:
            value = getattr(value, part, default)
        if value is default:
            break
    return value


_REQUIRED_INTERNAL_SERVICE_PORTS = (18103, 18104)


def check_docker(adapter: DockerAdapter) -> CheckResult:
    """Check Docker is installed and running, version >= 24.0."""
    ok, text = _run_text(adapter, ["docker", "--version"])
    if not ok:
        return CheckResult("docker", "fail", "Docker is unavailable.", "Install Docker Engine/Desktop and start the daemon.")
    version = _version_tuple(text)
    if version < (24, 0):
        return CheckResult("docker", "fail", f"Docker {text} is too old.", "Upgrade Docker to 24.0 or newer.")
    return CheckResult("docker", "pass", f"Docker available ({text}).")


def check_compose(adapter: DockerAdapter) -> CheckResult:
    """Check Docker Compose v2 is available, version >= 2.24."""
    ok, text = _run_text(adapter, ["docker", "compose", "version"])
    if not ok:
        return CheckResult("compose", "fail", "Docker Compose v2 is unavailable.", "Install or enable the docker compose plugin.")
    version = _version_tuple(text)
    if version < (2, 24):
        return CheckResult("compose", "fail", f"Compose {text} is too old.", "Upgrade Docker Compose to 2.24 or newer.")
    return CheckResult("compose", "pass", f"Compose available ({text}).")


def check_image_available(adapter: DockerAdapter, image: str) -> CheckResult:
    """Check if a Docker image exists locally."""
    ok, _ = _run_text(adapter, ["docker", "image", "inspect", image])
    if ok:
        return CheckResult(f"image:{image}", "pass", f"Image {image} is present locally.")
    return CheckResult(f"image:{image}", "warn", f"Image {image} is not present locally.", "Run superclaw-ctl pull or docker pull before starting services.")


def check_registry_auth(adapter: DockerAdapter, image: str) -> CheckResult:
    """Check if we can pull from the registry (docker manifest inspect)."""
    ok, text = _run_text(adapter, ["docker", "manifest", "inspect", image])
    if ok:
        return CheckResult(f"registry:{image}", "pass", f"Registry access verified for {image}.")
    if any(token in text.lower() for token in ("unauthorized", "denied", "forbidden", "authentication")):
        return CheckResult(f"registry:{image}", "fail", f"Registry authentication failed for {image}.", "Run docker login for the image registry.")
    return CheckResult(f"registry:{image}", "warn", f"Could not verify registry access for {image}.", text)


def check_ports_free(ports: list[int]) -> CheckResult:
    """Check if required ports are available."""
    busy: list[int] = []
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                busy.append(port)
    if busy:
        joined = ", ".join(str(port) for port in busy)
        return CheckResult("ports", "fail", f"Required ports are already in use: {joined}.", "Stop the conflicting service or reconfigure the ports.")
    return CheckResult("ports", "pass", "Required ports are free.")


def check_gpu_minimum_requirements(gpus: list[GPUInfo]) -> CheckResult:
    """Check that at least 4 Intel Arc Pro B70 GPUs are present (identified by PCI device ID E223)."""
    qualifying = [g for g in gpus if g.pci_id.upper() == _ARC_B70_PCI_ID]
    count = len(qualifying)
    if count < _MIN_B70_COUNT:
        return CheckResult(
            "gpu_minimum",
            "fail",
            f"Minimum GPU requirement not met: {count} Intel Arc Pro B70 found, need {_MIN_B70_COUNT}.",
            f"Install at least {_MIN_B70_COUNT} Intel® Arc™ Pro B70 Graphics cards (PCI ID 8086:E223).",
        )
    return CheckResult("gpu_minimum", "pass", f"GPU minimum met: {count}x Intel Arc Pro B70 found.")


def run_all_checks(adapter: DockerAdapter, config: Any, *, router_port: int = 8080) -> list[CheckResult]:
    """Run all prerequisite checks and return results."""
    images = [
        _config_get(config, "images.vllm"),
    ]
    ports = [*_REQUIRED_INTERNAL_SERVICE_PORTS, int(router_port)]
    results = [check_docker(adapter), check_compose(adapter), check_ports_free(ports)]
    for image in (image for image in images if image):
        results.append(check_image_available(adapter, image))
        results.append(check_registry_auth(adapter, image))
    return results
