from __future__ import annotations

"""Intel Arc GPU detection helpers for superclaw-ctl."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


@dataclass(slots=True)
class GPUInfo:
    """Detected Intel GPU details."""

    device_path: str
    name: str
    tiles: int
    driver_version: str
    pci_id: str = ""  # Uppercase hex device ID, e.g. "E223". Empty if unavailable.


def _run(*argv: str) -> str:
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _parse_xpu_discovery(text: str) -> list[GPUInfo]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        devices = payload.get("devices") or payload.get("device_list") or []
        infos: list[GPUInfo] = []
        for index, item in enumerate(devices):
            if not isinstance(item, dict):
                continue
            raw_pci = str(item.get("pci_device_id") or "")
            try:
                pci_id = format(int(raw_pci, 16), "X") if raw_pci else ""
            except ValueError:
                pci_id = ""
            infos.append(
                GPUInfo(
                    device_path=str(item.get("device_path") or f"/dev/dri/renderD{128 + index}"),
                    name=str(item.get("device_name") or item.get("name") or "Intel Arc GPU"),
                    tiles=int(item.get("tile_count") or item.get("tiles") or 1),
                    driver_version=str(item.get("driver_version") or item.get("driver") or ""),
                    pci_id=pci_id,
                )
            )
        if infos:
            return infos
    infos: list[GPUInfo] = []
    for block in re.split(r"\n\s*\n", text):
        if "Intel" not in block:
            continue
        path = re.search(r"(/dev/dri/renderD\d+)", block)
        name = re.search(r"(?:Device Name|Name)\s*[:=]\s*(.+)", block)
        tiles = re.search(r"(?:Tile(?: Count)?|Tiles)\s*[:=]\s*(\d+)", block)
        driver = re.search(r"(?:Driver(?: Version)?|Kernel)\s*[:=]\s*(.+)", block)
        infos.append(
            GPUInfo(
                device_path=path.group(1) if path else "/dev/dri/renderD128",
                name=name.group(1).strip() if name else "Intel Arc GPU",
                tiles=int(tiles.group(1)) if tiles else 1,
                driver_version=driver.group(1).strip() if driver else "",
            )
        )
    return infos


def _parse_lspci_pci_id(line: str) -> str:
    """Extract uppercase device ID from a `lspci -nn` line, e.g. '[8086:E223]' -> 'E223'."""
    match = re.search(r"\[8086:([0-9A-Fa-f]+)\]", line)
    return match.group(1).upper() if match else ""


def detect_gpus() -> list[GPUInfo]:
    """Detect Intel Arc GPUs. Returns empty list if none found."""
    render_nodes = sorted(Path("/dev/dri").glob("renderD*")) if Path("/dev/dri").exists() else []
    if shutil.which("xpu-smi"):
        discovered = _parse_xpu_discovery(_run("xpu-smi", "discovery", "-j") or _run("xpu-smi", "discovery"))
        if discovered and all(gpu.pci_id for gpu in discovered):
            # xpu-smi found GPUs with PCI IDs
            for index, info in enumerate(discovered):
                if info.device_path.startswith("/dev/dri/renderD") and index < len(render_nodes):
                    info.device_path = str(render_nodes[index])
            return discovered
        # xpu-smi either found no devices or they lack pci_id, fallback to use lspci
    lspci = _run("lspci", "-nn") if shutil.which("lspci") else ""
    intel_lines = [line for line in lspci.splitlines() if "Intel" in line and ("VGA" in line or "Display" in line)]
    return [
        GPUInfo(
            device_path=str(path),
            name=intel_lines[index].split(": ", 1)[-1] if index < len(intel_lines) else "Intel Arc GPU",
            tiles=1,
            driver_version=os.uname().release if hasattr(os, "uname") else "",
            pci_id=_parse_lspci_pci_id(intel_lines[index]) if index < len(intel_lines) else "",
        )
        for index, path in enumerate(render_nodes)
    ]


def check_gpu_access() -> list[str]:
    """Check GPU accessibility. Returns list of warnings."""
    warnings: list[str] = []
    dri = Path("/dev/dri")
    if os.name == "nt":
        return ["GPU access checks are only available on Linux hosts."]
    if not dri.exists():
        return ["/dev/dri is missing; GPU devices are not exposed."]
    render_nodes = sorted(dri.glob("renderD*"))
    if not render_nodes:
        warnings.append("No /dev/dri/renderD* devices found.")
    if hasattr(os, "getgroups"):
        import grp

        groups = {grp.getgrgid(gid).gr_name for gid in os.getgroups()}
        if groups.isdisjoint({"render", "video"}):
            warnings.append("Current user is not in the render or video group.")
    for path in render_nodes:
        if not os.access(path, os.R_OK | os.W_OK):
            warnings.append(f"{path} is not readable and writable by the current user.")
    return warnings


def gpu_utilization() -> list[dict] | None:
    """Get GPU utilization via xpu-smi. Returns None if unavailable."""
    if not shutil.which("xpu-smi"):
        return None
    for argv in (("xpu-smi", "dump", "-j"), ("xpu-smi", "stats", "-j"), ("xpu-smi", "discovery", "-j")):
        output = _run(*argv)
        if not output:
            continue
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            devices = payload.get("devices") or payload.get("device_list") or payload.get("data")
            if isinstance(devices, list):
                return [item for item in devices if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
    return None
