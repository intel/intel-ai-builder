from __future__ import annotations

import os
import stat
import tomllib
import uuid
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import BaseModel, Field, ValidationError

from superclaw_ctl.errors import ConfigError, SecretsError

_CONFIG_FILE_NAME = "config.toml"
_SECRETS_FILE_NAME = "secrets.toml"
_REJECTED_TOKENS = frozenset({"", "password", "secret", "admin", "test"})
# Escape hatch: set this env var truthy to allow known demo/weak tokens
# An empty key is always rejected regardless, since it cannot authenticate anything.
_ALLOW_DEMO_KEY_ENV = "SUPERCLAW_ALLOW_DEMO_KEY"
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
_CONFIG_ENV_OVERRIDES = {
    "SUPERCLAW_MODELS_DIR": ("paths", "models_dir"),
}
_SECRETS_ENV_OVERRIDES = {
    "SUPERCLAW_VLLM_API_KEY": "vllm_api_key",
}


class ImagesConfig(BaseModel):
    vllm: str = "intel/llm-scaler-vllm:0.14.0-b8.3"


class PathsConfig(BaseModel):
    models_dir: str = "~/.models"
    compose_dir: str = "~/.config/superclaw-ctl/compose"
    logs_dir: str = "~/.config/superclaw-ctl/logs"


class ComposeConfig(BaseModel):
    project_name: str = "superclaw"
    extra_files: list[str] = Field(default_factory=list)


class VllmWatchdogConfig(BaseModel):
    enabled: bool = True
    interval_s: int = 60
    consecutive_failures: int = 3
    canary_expected: str = "Hello"
    max_restart_attempts: int = 5   # 0 = unlimited
    restart_window_minutes: int = 60  # reset counter after this many minutes of healthy operation


class VllmConfig(BaseModel):
    watchdog: VllmWatchdogConfig = Field(default_factory=VllmWatchdogConfig)


class Config(BaseModel):
    config_version: int = 1
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    compose: ComposeConfig = Field(default_factory=ComposeConfig)
    vllm: VllmConfig = Field(default_factory=VllmConfig)


class Secrets(BaseModel):
    vllm_api_key: str = ""


JsonDict = dict[str, Any]


def get_config_dir() -> Path:
    return Path.home() / ".config" / "superclaw-ctl"


def load_config() -> Config:
    path = _config_path()
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}",
            hint="Run `superclaw-ctl init` to create a config file.",
        )

    data = _read_toml(path, ConfigError, "config")
    merged = _merge_dict(Config().model_dump(mode="python"), data)
    merged = _merge_dict(merged, _config_env_data())
    return _validate_model(Config, merged, ConfigError, "config")


def save_config(config: Config) -> None:
    _write_toml_atomic(_config_path(), config.model_dump(mode="python"), error_type=ConfigError)


def load_secrets() -> Secrets:
    path = _secrets_path()
    if not path.exists():
        raise SecretsError(
            f"Secrets file not found: {path}",
            hint="Run `superclaw-ctl init` to generate secrets.",
        )

    _verify_secrets_permissions(path)
    data = _read_toml(path, SecretsError, "secrets")
    merged = _merge_dict(Secrets().model_dump(mode="python"), data)
    merged = _merge_dict(merged, _secrets_env_data())
    secrets = _validate_model(Secrets, merged, SecretsError, "secrets")
    _raise_for_rejected_secret_values(secrets)
    return secrets


def save_secrets(secrets: Secrets) -> None:
    _raise_for_rejected_secret_values(secrets)
    _write_toml_atomic(
        _secrets_path(),
        secrets.model_dump(mode="python"),
        chmod_mode=0o600,
        error_type=SecretsError,
    )


def config_exists() -> bool:
    return _config_path().exists()


def secrets_exists() -> bool:
    return _secrets_path().exists()


def validate_secrets(secrets: Secrets) -> list[str]:
    warnings: list[str] = []
    values = secrets.model_dump(mode="python")

    for name, value in values.items():
        normalized = value.strip()
        rejection_reason = _rejected_token_reason(normalized)
        if rejection_reason is not None:
            warnings.append(f"{name} {rejection_reason}.")
            continue
        if len(normalized) < 24:
            warnings.append(f"{name} is shorter than the recommended 24 characters.")
        if any(char.isspace() for char in value):
            warnings.append(f"{name} contains whitespace; confirm it was copied correctly.")

    unique_values = {value.strip() for value in values.values() if value.strip()}
    if len(unique_values) == 1 and len([value for value in values.values() if value.strip()]) > 1:
        warnings.append("Multiple secrets reuse the same token; generate unique values for each service.")

    return warnings


def _config_path() -> Path:
    return get_config_dir() / _CONFIG_FILE_NAME


def _secrets_path() -> Path:
    return get_config_dir() / _SECRETS_FILE_NAME


def _read_toml(path: Path, error_type: type[ConfigError] | type[SecretsError], label: str) -> JsonDict:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise error_type(
            f"Failed to parse {label} file: {path}",
            hint="Fix the TOML syntax or recreate the file.",
        ) from exc
    except OSError as exc:
        raise error_type(f"Failed to read {label} file: {path}") from exc

    if not isinstance(data, dict):
        raise error_type(f"Invalid {label} file: expected a TOML table at the top level.")
    return data


def _validate_model(
    model_type: type[Config] | type[Secrets],
    data: JsonDict,
    error_type: type[ConfigError] | type[SecretsError],
    label: str,
) -> Config | Secrets:
    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise error_type(
            f"Invalid {label} file values.",
            hint=str(exc),
        ) from exc


def _config_env_data() -> JsonDict:
    data: JsonDict = {}
    for env_name, path_parts in _CONFIG_ENV_OVERRIDES.items():
        if env_name not in os.environ:
            continue
        current = data
        for part in path_parts[:-1]:
            current = current.setdefault(part, {})
        current[path_parts[-1]] = os.environ[env_name]
    return data


def _secrets_env_data() -> JsonDict:
    data: JsonDict = {}
    for env_name, field_name in _SECRETS_ENV_OVERRIDES.items():
        if env_name in os.environ:
            data[field_name] = os.environ[env_name]
    return data


def _merge_dict(base: JsonDict, override: JsonDict) -> JsonDict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _write_toml_atomic(
    path: Path,
    data: JsonDict,
    *,
    error_type: type[ConfigError] | type[SecretsError],
    chmod_mode: int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"

    try:
        payload = tomli_w.dumps(data).encode("utf-8")
        with temp_path.open("wb") as handle:
            handle.write(payload)
        if chmod_mode is not None and os.name != "nt":
            os.chmod(temp_path, chmod_mode)
        os.replace(temp_path, path)
        if chmod_mode is not None and os.name != "nt":
            os.chmod(path, chmod_mode)
    except OSError as exc:
        raise error_type(f"Failed to write file: {path}") from exc
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _verify_secrets_permissions(path: Path) -> None:
    if os.name == "nt":
        return

    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SecretsError(
            f"Secrets file permissions are too open: {path}",
            hint="Run `chmod 600 ~/.config/superclaw-ctl/secrets.toml`.",
        )


def _raise_for_rejected_secret_values(secrets: Secrets) -> None:
    for name, value in secrets.model_dump(mode="python").items():
        rejection_reason = _rejected_token_reason(value.strip())
        if rejection_reason is not None:
            raise SecretsError(
                f"Invalid secret `{name}`: {rejection_reason}.",
                hint="Generate a strong random token and save it again.",
            )


def _demo_key_allowed() -> bool:
    return os.environ.get(_ALLOW_DEMO_KEY_ENV, "").strip().lower() in _TRUTHY_ENV_VALUES


def _rejected_token_reason(value: str) -> str | None:
    if value == "":
        return "cannot be empty"
    if _demo_key_allowed():
        return None
    lowered = value.lower()
    if lowered in _REJECTED_TOKENS:
        return "uses a rejected demo token"
    return None
