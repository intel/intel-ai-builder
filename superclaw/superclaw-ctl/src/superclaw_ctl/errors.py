from __future__ import annotations

from typing import ClassVar


class SuperclawCtlError(Exception):
    """Base error type for user-facing CLI failures."""

    default_exit_code: ClassVar[int] = 1

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    @property
    def exit_code(self) -> int:
        return self.default_exit_code

    def __str__(self) -> str:
        return self.message


class CommandError(SuperclawCtlError):
    """Error raised for failed external command execution."""

    def __init__(
        self,
        message_or_command: str | tuple[str, ...] | list[str],
        returncode: int | None = None,
        stderr: str = "",
        stdout: str = "",
        *,
        hint: str | None = None,
    ) -> None:
        if isinstance(message_or_command, str):
            message = message_or_command
            command: tuple[str, ...] = ()
        else:
            command = tuple(message_or_command)
            details = stderr or stdout or "command failed"
            suffix = f" (exit code {returncode})" if returncode is not None else ""
            message = f"{' '.join(command)}{suffix}: {details}"
        super().__init__(message, hint=hint)
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout


class ConfigError(SuperclawCtlError):
    default_exit_code = 2


class DockerError(CommandError):
    default_exit_code = 3


class ComposeError(CommandError):
    default_exit_code = 4


class SecretsError(SuperclawCtlError):
    default_exit_code = 5


class GPUError(SuperclawCtlError):
    default_exit_code = 6


class HealthError(SuperclawCtlError):
    default_exit_code = 7


class ImageError(SuperclawCtlError):
    default_exit_code = 8


class ModelError(SuperclawCtlError):
    default_exit_code = 9
