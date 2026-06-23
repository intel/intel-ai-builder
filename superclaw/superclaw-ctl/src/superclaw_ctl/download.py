"""Model download and integrity verification using huggingface_hub.

Downloads full PyTorch/safetensors model repositories for vLLM serving.
Verifies integrity by comparing local snapshot revision against remote HEAD
and optionally checking LFS SHA256 for individual files.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from huggingface_hub import HfApi, snapshot_download

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
    """Download or sync a model snapshot from HuggingFace.

    Always calls snapshot_download, which is incremental: it checks each file's
    ETag against the remote manifest and only fetches missing or changed files.

    If the model files are already locally present and the remote is unreachable
    (network error), the download is treated as a warning rather than a hard
    failure so that init can still proceed with the local files.

    On network failures without local files, automatically retries via hf-mirror.com.
    Auth/404 errors are not retried.
    """
    local_dir = models_dir / entry.local_dir_name

    # Determine whether local files are likely usable for offline fallback.
    # A structurally complete snapshot can still be partial for sharded models.
    # Apply the same 85% size sanity check used in init when an approximate size
    # is available.
    looks_complete = _snapshot_looks_complete(local_dir)
    was_locally_present = looks_complete
    approx_size = getattr(entry, "size_bytes_approx", 0)
    if looks_complete and approx_size > 0:
        from .models import get_dir_size

        actual_size = get_dir_size(local_dir)
        was_locally_present = actual_size >= approx_size * 0.85

    if was_locally_present:
        if on_progress:
            on_progress(f"{entry.name}: verifying files and syncing any missing shards...")
    else:
        if on_progress:
            on_progress(f"{entry.name}: downloading from {entry.repo}...")

    # snapshot_download is incremental: downloads only missing / changed files
    primary_exc = _attempt_snapshot_download(entry, local_dir, endpoint=_HF_PRIMARY_ENDPOINT)
    if primary_exc is None:
        if on_progress:
            on_progress(f"{entry.name}: {'verified ✓' if was_locally_present else 'download complete.'}")
        return DownloadResult(model_id=entry.id, local_dir=local_dir, already_present=was_locally_present)

    # Network errors: special handling when files are already present locally
    if _is_network_error(primary_exc):
        if was_locally_present:
            # Files are locally present; can't sync against remote right now.
            # Treat as a warning so init can still proceed.
            hint = _proxy_guidance_hint(primary_exc)
            warn = (
                "Local model files are present, but remote sync failed. "
                f"{primary_exc}{hint}"
            )
            if on_progress:
                on_progress(f"{entry.name}: using local files (remote unreachable).")
            return DownloadResult(model_id=entry.id, local_dir=local_dir, already_present=True, error=warn)

        # No local files — retry via hf-mirror.com
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

    # Non-network error (e.g. 401, 404)
    if was_locally_present:
        # Local files exist; treat the remote error as a warning rather than blocking init.
        hint = _proxy_guidance_hint(primary_exc)
        warn = f"Remote sync failed: {primary_exc}{hint}"
        _log.warning("Remote sync failed for %s (local files present): %s", entry.repo, primary_exc)
        return DownloadResult(model_id=entry.id, local_dir=local_dir, already_present=True, error=warn)

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
    except Exception as exc:
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

    if not _snapshot_looks_complete(local_dir):
        result.error = "Model files look incomplete (missing config.json or weight files)."
        return result

    local_consistency_error = _validate_local_snapshot_consistency(local_dir)
    if local_consistency_error:
        result.error = local_consistency_error
        return result

    approx = max(0, int(getattr(entry, "size_bytes_approx", 0) or 0))
    if approx > 0:
        from .models import format_size
        weight_size = 0
        for pattern in ("*.safetensors", "model*.bin", "pytorch_model*.bin", "*.gguf"):
            for path in local_dir.glob(pattern):
                try:
                    if path.is_file():
                        weight_size += path.stat().st_size
                except OSError:
                    continue
        if weight_size and weight_size < approx * 0.85:
            result.error = (
                f"Model appears partially downloaded: {format_size(weight_size)} present, "
                f"{format_size(approx)} expected."
            )
            return result

    # Local integrity checks passed
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

    except Exception as exc:
        hint = _proxy_guidance_hint(exc)
        _log.warning("Remote verification failed for %s: %s%s", entry.repo, exc, hint)
        result.remote_matches = None
        result.error = f"Remote check failed: {exc}{hint}"

    return result


def snapshot_looks_complete(local_dir: Path) -> bool:
    """Quick heuristic: directory exists with config.json and at least one shard.

    Public wrapper used by callers outside this module (e.g. the init pre-flight check).
    """
    return _snapshot_looks_complete(local_dir)


def _snapshot_looks_complete(local_dir: Path) -> bool:
    """Quick heuristic: directory exists with config.json and at least one shard."""
    if not local_dir.is_dir():
        return False
    if not (local_dir / "config.json").is_file():
        return False
    # Check for weights (or known shard index layouts for sharded repos)
    has_weights = (
        any(local_dir.glob("*.safetensors"))
        or any(local_dir.glob("model*.bin"))
        or (local_dir / "pytorch_model.bin").is_file()
        or any(local_dir.glob("pytorch_model-*.bin"))
        or any(local_dir.glob("*.gguf"))
        or (local_dir / "model.safetensors.index.json").is_file()
        or (local_dir / "pytorch_model.bin.index.json").is_file()
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
) -> bool | None:
    """Verify SHA256 of key model files against HuggingFace remote."""
    # Verify one representative weight shard when revision metadata is unavailable
    # Support both safetensors and sharded pytorch layouts
    candidate_files = sorted(local_dir.glob("*.safetensors"))
    if not candidate_files:
        candidate_files = sorted(local_dir.glob("model*.bin"))
    if not candidate_files:
        candidate_files = sorted(local_dir.glob("pytorch_model*.bin"))
    if not candidate_files:
        return None  # Can't verify

    target_file = candidate_files[0]
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
        return None  # Can't verify

    if not paths_info:
        return None

    remote_entry = paths_info[0]
    lfs = getattr(remote_entry, "lfs", None)
    if lfs is None:
        return None

    remote_sha = getattr(lfs, "sha256", None)
    if not remote_sha:
        return None

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


def _validate_local_snapshot_consistency(local_dir: Path) -> str | None:
    """Validate local shard integrity from known HF index files when present."""
    index_files = (
        local_dir / "model.safetensors.index.json",
        local_dir / "pytorch_model.bin.index.json",
    )

    for index_path in index_files:
        if not index_path.is_file():
            continue
        try:
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return f"Invalid shard index file {index_path.name}: {exc}"

        weight_map = index_payload.get("weight_map")
        if not isinstance(weight_map, dict) or not weight_map:
            return f"Invalid shard index file {index_path.name}: missing weight_map entries."

        shard_files = {str(v) for v in weight_map.values() if isinstance(v, str)}
        if not shard_files:
            return f"Invalid shard index file {index_path.name}: no shard filenames listed."

        for shard_name in shard_files:
            shard_candidate = Path(shard_name)
            if shard_candidate.is_absolute() or ".." in shard_candidate.parts:
                return f"Invalid shard index file {index_path.name}: unsafe shard path {shard_name!r}"
            shard_path = local_dir / shard_candidate
            if not shard_path.is_file():
                return f"Missing shard files: {shard_name}"
            try:
                if shard_path.stat().st_size <= 0:
                    return f"Shard file is empty: {shard_name}"
            except OSError as exc:
                return f"Unable to read shard file {shard_name}: {exc}"

    return None
