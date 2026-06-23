"""vLLM model registry.

Provides the model manifest for Linux/vLLM deployments using full PyTorch
repos from HuggingFace (safetensors format).
"""

from __future__ import annotations

import importlib.resources
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class VllmModelEntry:
    id: str
    name: str
    role: str  # "chat" or "embedding"
    repo: str  # HuggingFace repo_id e.g. "Qwen/Qwen3-Coder-Next"
    revision: str = "main"
    local_dir_name: str = ""
    size_bytes_approx: int = 0  # Approximate on-disk size after download; 0 means unknown
    vllm_args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VllmRegistry:
    active_chat_model: str
    active_embedding_model: str
    models: list[VllmModelEntry]

    def get_active_chat(self) -> VllmModelEntry | None:
        return next((m for m in self.models if m.id == self.active_chat_model), None)

    def get_active_embedding(self) -> VllmModelEntry | None:
        return next((m for m in self.models if m.id == self.active_embedding_model), None)

    def get_active_models(self) -> list[VllmModelEntry]:
        """Return the active chat + embedding models."""
        result = []
        chat = self.get_active_chat()
        if chat:
            result.append(chat)
        embed = self.get_active_embedding()
        if embed:
            result.append(embed)
        return result


def load_registry(path: Path | None = None) -> VllmRegistry:
    """Load the vLLM model registry from a JSON file.

    If no path is given, loads the bundled vllm_models.json.
    """
    if path is None:
        resource = importlib.resources.files("superclaw_ctl").joinpath("vllm_models.json")
        raw = json.loads(resource.read_text(encoding="utf-8"))
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))

    models = [
        VllmModelEntry(
            id=m["id"],
            name=m["name"],
            role=m["role"],
            repo=m["repo"],
            revision=m.get("revision", "main"),
            local_dir_name=m.get("local_dir_name", m["id"]),
            size_bytes_approx=m.get("size_bytes_approx", 0),
            vllm_args=m.get("vllm_args", {}),
        )
        for m in raw["models"]
    ]

    return VllmRegistry(
        active_chat_model=raw["active_chat_model"],
        active_embedding_model=raw["active_embedding_model"],
        models=models,
    )
