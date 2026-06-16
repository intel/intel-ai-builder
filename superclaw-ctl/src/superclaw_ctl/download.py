"""Model download and integrity verification using huggingface_hub.

Downloads full PyTorch/safetensors model repositories for vLLM serving.
Verifies integrity by comparing local snapshot revision against remote HEAD
and optionally checking LFS SHA256 for individual files.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from huggingface_hub import HfApi, snapshot_download
from huggingface_hub.utils import HfHubHTTPError

from .registry import VllmModelEntry

_log = logging.getLogger(__name__)
_HF_NETWORK_TIMEOUT_SECONDS = 30
_HF_PRIMARY_ENDPOINT = "https://huggingface.co"
_HF_MIRROR_ENDPOINT = "https://hf-mirror.com"


@dataclass(slots=True)
class DownloadResult:
    model_id: str
    local_dir: Path
    already_present: bool = False
    error: str | None = None


@dataclass(slots=True)
class VerifyResult:
    model_id: str
    local_valid: bool = False
    remote_matches: bool | None = None
    local_revision: str = ""
    remote_revision: str = ""
    error: str | None = None


def download_model(
    entry: VllmModelEntry,
    models_dir: Path,
    *,
    on_progress: Callable[[str], None] | None = None,
) -> DownloadResult:
    """Download a model snapshot from HuggingFace, with automatic fallback to hf-mirror.com.

    Tries huggingface.co first. On network-class errors (timeouts, connection failures,
    DNS issues), automatically retries using hf-mirror.com as an alternative endpoint.
    Auth/404 errors are not retried. Proxy settings (HTTP_PROXY, HTTPS_PROXY) apply to
    both endpoints.
    """
    local_dir = models_dir / entry.local_dir_name

    # Quick check: if model directory exists with config.json, likely present
    if _snapshot_looks_complete(local_dir):
        if on_progress:
            on_progress(f"{entry.name}: already present, verifying...")
        verification = verify_model(entry, models_dir, check_remote=True)
        if verification.local_valid and verification.remote_matches is not False:
            if verification.error:
                return DownloadResult(
                    model_id=entry.id,
                    local_dir=local_dir,
                    already_present=True,
                    error=(
                        "Local model files are present, but remote verification failed. "
                        f"{verification.error}"
                    ),
                )
            return DownloadResult(
                model_id=entry.id, local_dir=local_dir, already_present=True
            )
        if on_progress:
            on_progress(f"{entry.name}: integrity check failed, re-downloading...")

    if on_progress:
        on_progress(f"{entry.name}: downloading from {entry.repo}...")

    # Try primary endpoint (huggingface.co)
    primary_exc = _attempt_snapshot_download(entry, local_dir, endpoint=_HF_PRIMARY_ENDPOINT)
    if primary_exc is None:
        if on_progress:
            on_progress(f"{entry.name}: download complete.")
        return DownloadResult(model_id=entry.id, local_dir=local_dir)

    # On network errors only, retry via hf-mirror.com
    if _is_network_error(primary_exc):
        _log.debug(
            "huggingface.co unreachable for %s (%s), retrying via hf-mirror.com...",
            entry.repo,
            primary_exc,
        )
        if on_progress:
            on_progress(
                f"{entry.name}: huggingface.co unreachable, retrying via hf-mirror.com..."
            )
        mirror_exc = _attempt_snapshot_download(entry, local_dir, endpoint=_HF_MIRROR_ENDPOINT)
        if mirror_exc is None:
            if on_progress:
                on_progress(f"{entry.name}: download complete (via hf-mirror.com).")
            return DownloadResult(model_id=entry.id, local_dir=local_dir)

        _log.error(
            "Both endpoints failed for %s. Primary: %s; Mirror: %s",
            entry.repo,
            primary_exc,
            mirror_exc,
        )
        return DownloadResult(
            model_id=entry.id,
            local_dir=local_dir,
            error=(
                f"huggingface.co: {primary_exc}; hf-mirror.com: {mirror_exc}"
                f"{_proxy_guidance_hint(primary_exc)}"
            ),
        )

    # Non-network error (e.g. 401, 404) — don't retry
    _log.error("Failed to download %s: %s", entry.repo, primary_exc)
    hint = _proxy_guidance_hint(primary_exc)
    return DownloadResult(
        model_id=entry.id,
        local_dir=local_dir,
        error=f"{primary_exc}{hint}",
    )


def _attempt_snapshot_download(
    entry: VllmModelEntry,
    local_dir: Path,
    endpoint: str,
) -> Exception | None:
    """Try snapshot_download against the given endpoint. Returns None on success, the exception on failure."""
    try:
        snapshot_download(
            repo_id=entry.repo,
            revision=entry.revision,
            local_dir=str(local_dir),
            etag_timeout=_HF_NETWORK_TIMEOUT_SECONDS,
            endpoint=endpoint,
        )
        return None
    except (HfHubHTTPError, OSError, Exception) as exc:
        return exc


def verify_model(
    entry: VllmModelEntry,
    models_dir: Path,
    *,
    check_remote: bool = True,
) -> VerifyResult:
    """Verify model integrity.

    Checks:
    1. Local snapshot directory exists and includes config.json
    2. If check_remote: local revision matches HuggingFace remote HEAD
    3. If check_remote: key LFS files have correct SHA256
    """
    local_dir = models_dir / entry.local_dir_name
    result = VerifyResult(model_id=entry.id)

    if not local_dir.is_dir():
        result.error = f"Directory not found: {local_dir}"
        return result

    # Check local completeness
    config_path = local_dir / "config.json"
    if not config_path.is_file():
        result.error = "Missing config.json"
        return result

    # Read local revision from snapshot metadata
    local_rev = _read_local_revision(local_dir)
    result.local_revision = local_rev
    result.local_valid = True

    if not check_remote:
        return result

    # Compare with remote HEAD
    try:
        api = HfApi()
        model_info = api.model_info(
            entry.repo,
            revision=entry.revision,
            timeout=_HF_NETWORK_TIMEOUT_SECONDS,
        )
        result.remote_revision = model_info.sha or ""

        if local_rev and model_info.sha:
            result.remote_matches = local_rev == model_info.sha
        else:
            # Can't compare revisions; check key files via SHA
            result.remote_matches = _verify_key_files(api, entry, local_dir)

    except HfHubHTTPError as exc:
        hint = _proxy_guidance_hint(exc)
        _log.warning("Remote verification failed for %s: %s%s", entry.repo, exc, hint)
        result.remote_matches = None
        result.error = f"Remote check failed: {exc}{hint}"
    except Exception as exc:
        hint = _proxy_guidance_hint(exc)
        _log.warning("Unexpected error verifying %s: %s%s", entry.repo, exc, hint)
        result.remote_matches = None
        result.error = f"Remote check failed: {exc}{hint}"

    return result


def _snapshot_looks_complete(local_dir: Path) -> bool:
    """Quick heuristic: directory exists with config.json and at least one shard."""
    if not local_dir.is_dir():
        return False
    if not (local_dir / "config.json").is_file():
        return False
    # Check for safetensors or bin files
    has_weights = (
        any(local_dir.glob("*.safetensors"))
        or any(local_dir.glob("model*.bin"))
        or any(local_dir.glob("*.gguf"))
    )
    return has_weights


def _read_local_revision(local_dir: Path) -> str:
    """Read the commit SHA from HuggingFace snapshot metadata.

    snapshot_download stores metadata in .cache/huggingface/ or in
    refs/main under the cache dir. We also check for a .huggingface/
    directory that newer versions create.
    """
    # Modern layout: snapshot_download with local_dir creates a
    # .huggingface/commit_hash file
    commit_file = local_dir / ".huggingface" / "commit_hash"
    if commit_file.is_file():
        return commit_file.read_text(encoding="utf-8").strip()

    # Fallback: check refs/main in HF cache structure
    refs_main = local_dir / "refs" / "main"
    if refs_main.is_file():
        return refs_main.read_text(encoding="utf-8").strip()

    return ""


def _verify_key_files(
    api: HfApi, entry: VllmModelEntry, local_dir: Path
) -> bool:
    """Verify SHA256 of key model files against HuggingFace remote."""
    # Find safetensors files to verify (just check the first shard)
    safetensors = sorted(local_dir.glob("*.safetensors"))
    if not safetensors:
        safetensors = sorted(local_dir.glob("model*.bin"))
    if not safetensors:
        return True  # No files to verify

    target_file = safetensors[0]
    relative_path = target_file.name

    try:
        paths_info = api.get_paths_info(
            repo_id=entry.repo,
            paths=[relative_path],
            repo_type="model",
            revision=entry.revision,
        )
    except Exception as exc:
        _log.warning("get_paths_info failed for %s: %s", entry.repo, exc)
        return True  # Can't verify, assume OK

    if not paths_info:
        return True

    remote_entry = paths_info[0]
    lfs = getattr(remote_entry, "lfs", None)
    if lfs is None:
        return True

    remote_sha = getattr(lfs, "sha256", None)
    if not remote_sha:
        return True

    # Compute local SHA256
    local_sha = _sha256_file(target_file)
    return local_sha.lower() == remote_sha.lower()


def _sha256_file(path: Path) -> str:
    """Compute SHA256 of a file in chunks to handle large files."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024 * 8):  # 8MB chunks
            h.update(chunk)
    return h.hexdigest()


def _is_network_error(exc: Exception) -> bool:
    """Return True if the exception looks like a transient network failure."""
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "timed out",
            "timeout",
            "failed to connect",
            "connection",
            "name resolution",
            "temporary failure",
            "proxy",
            "network is unreachable",
            "max retries exceeded",
            "newconnectionerror",
            "failed to establish",
        )
    )


def _proxy_guidance_hint(exc: Exception) -> str:
    if not _is_network_error(exc):
        return ""

    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not (http_proxy or https_proxy):
        return "\nCheck proxy settings: set HTTP_PROXY/HTTPS_PROXY if your network requires a proxy."

    return "\nCheck proxy settings: verify HTTP_PROXY/HTTPS_PROXY and NO_PROXY are correct for your environment."
