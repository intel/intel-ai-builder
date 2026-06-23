from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ModelInfo:
    name: str
    path: Path
    size_bytes: int = 0
    architecture: str = ""
    num_parameters: str = ""
    quantization: str = ""
    context_length: int = 0
    vocab_size: int = 0
    model_type: str = ""


def list_models(models_dir: Path) -> list[ModelInfo]:
    """Scan models_dir for model subdirectories and return info."""
    if not models_dir.is_dir():
        return []

    return [
        _build_model_info(model_path)
        for model_path in sorted(
            (path for path in models_dir.iterdir() if path.is_dir()),
            key=lambda path: path.name.lower(),
        )
    ]


def get_model_info(models_dir: Path, name: str) -> ModelInfo | None:
    """Get detailed info for a specific model."""
    model_path = models_dir / name
    if not model_path.is_dir():
        return None
    return _build_model_info(model_path)


def get_dir_size(path: Path) -> int:
    """Recursively calculate directory size in bytes."""
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string (e.g., '22.3 GB')."""
    size = float(max(size_bytes, 0))
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def _parse_config_json(config_path: Path) -> dict:
    """Parse model config.json and extract relevant fields."""
    if not config_path.is_file():
        return {}

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}

    architecture = ""
    architectures = raw.get("architectures")
    if isinstance(architectures, list) and architectures:
        architecture = str(architectures[0])
    elif isinstance(architectures, str):
        architecture = architectures

    return {
        "architecture": architecture,
        "context_length": _as_int(
            raw.get("max_position_embeddings") or raw.get("model_max_length")
        ),
        "vocab_size": _as_int(raw.get("vocab_size")),
        "model_type": str(raw.get("model_type") or ""),
        "quantization": _extract_quantization(raw, config_path.parent.name),
        "num_parameters": _extract_num_parameters(raw, config_path.parent.name),
    }


def _build_model_info(model_path: Path) -> ModelInfo:
    config = _parse_config_json(model_path / "config.json")
    return ModelInfo(
        name=model_path.name,
        path=model_path,
        size_bytes=get_dir_size(model_path),
        architecture=str(config.get("architecture") or ""),
        num_parameters=str(config.get("num_parameters") or ""),
        quantization=str(config.get("quantization") or ""),
        context_length=_as_int(config.get("context_length")),
        vocab_size=_as_int(config.get("vocab_size")),
        model_type=str(config.get("model_type") or ""),
    )


def _as_int(value: object) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _extract_quantization(config: dict, model_name: str) -> str:
    quantization_config = config.get("quantization_config")
    if isinstance(quantization_config, dict):
        quant_method = quantization_config.get("quant_method")
        if isinstance(quant_method, str) and quant_method:
            return quant_method
        bits = quantization_config.get("bits")
        if bits is not None:
            return f"int{bits}"

    for key in ("quantization", "torch_dtype"):
        value = config.get(key)
        if isinstance(value, str) and value:
            normalized = {
                "float16": "fp16",
                "float32": "fp32",
                "bfloat16": "bf16",
            }.get(value.lower(), value)
            return normalized

    match = re.search(
        r"(?i)(Q\d(?:_[A-Z]+(?:_[A-Z]+)*)?|fp(?:8|16|32)|bf16|int(?:4|8))",
        model_name,
    )
    return match.group(1) if match else ""


def _extract_num_parameters(config: dict, model_name: str) -> str:
    for key in ("num_parameters", "parameter_count"):
        value = config.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, (int, float)) and value > 0:
            return _humanize_parameter_count(float(value))

    match = re.search(r"(?i)(\d+(?:\.\d+)?)\s*([BMK])", model_name)
    if not match:
        return ""

    value = float(match.group(1))
    suffix = match.group(2).upper()
    return f"{value:g}{suffix}"


def _humanize_parameter_count(value: float) -> str:
    for suffix, scale in (("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if value >= scale:
            amount = value / scale
            return f"{amount:.1f}{suffix}" if amount % 1 else f"{int(amount)}{suffix}"
    return str(int(value))
