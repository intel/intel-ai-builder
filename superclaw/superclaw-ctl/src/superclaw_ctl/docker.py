from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from .errors import ComposeError, DockerError


@dataclass(slots=True)
class DockerResult:
    returncode: int
    stdout: str
    stderr: str


class DockerAdapter:
    def __init__(self, secrets_to_redact: list[str] | None = None):
        self._redact = [secret for secret in secrets_to_redact or [] if secret]

    def run(
        self,
        args: list[str],
        *,
        timeout: int = 60,
        capture: bool = True,
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> DockerResult:
        """Run a docker command and return the result."""
        command = self._command(args)
        try:
            completed = subprocess.run(
                command,
                check=False,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=self._env(env),
                stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise self._command_error(command, 127, stderr=str(exc)) from exc
        except subprocess.TimeoutExpired as exc:
            stdout = self._decode(exc.stdout)
            stderr = self._decode(exc.stderr) or f"timed out after {timeout}s"
            raise self._command_error(command, None, stdout=stdout, stderr=stderr) from exc

        result = DockerResult(
            returncode=completed.returncode,
            stdout=self._redact_text(completed.stdout or ""),
            stderr=self._redact_text(completed.stderr or ""),
        )
        if completed.returncode != 0:
            raise self._command_error(command, completed.returncode, result.stdout, result.stderr)
        return result

    def run_json(self, args: list[str], **kwargs) -> list[dict] | dict:
        """Run and parse JSON output (supports both JSON arrays and NDJSON)."""
        result = self.run(args, **kwargs)
        if not result.stdout.strip():
            return []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Docker compose ps outputs one JSON object per line (NDJSON)
            lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
            try:
                data = [json.loads(line) for line in lines]
            except json.JSONDecodeError as exc:
                raise self._command_error(self._command(args), result.returncode, result.stdout, "invalid JSON output") from exc
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                return data
        elif isinstance(data, dict):
            return data
        raise self._command_error(self._command(args), result.returncode, result.stdout, "expected JSON object or array")

    def stream(
        self,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> Generator[str, None, int]:
        """Stream output line by line, yield each line. Returns exit code."""
        command = self._command(args)
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=cwd,
                env=self._env(env),
            )
        except FileNotFoundError as exc:
            raise self._command_error(command, 127, stderr=str(exc)) from exc

        tail: list[str] = []
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = self._redact_text(raw_line.rstrip("\r\n"))
            if line:
                tail.append(line)
                tail[:] = tail[-20:]
            yield line

        returncode = process.wait()
        if returncode != 0:
            raise self._command_error(command, returncode, stderr="\n".join(tail))
        return returncode

    def passthrough(
        self,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> None:
        """Run command with stdout/stderr directly attached to the terminal (no capture).

        This preserves ANSI escape codes for in-place progress rendering (e.g. docker pull).
        """
        command = self._command(args)
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=self._env(env),
            )
        except FileNotFoundError as exc:
            raise self._command_error(command, 127, stderr=str(exc)) from exc
        if result.returncode != 0:
            raise self._command_error(command, result.returncode)

    def docker_version(self) -> str | None:
        """Get docker version string, or None if not found."""
        try:
            return self.run(["version", "--format", "{{.Client.Version}}"], timeout=10).stdout.strip() or None
        except DockerError:
            return None

    def compose_version(self) -> str | None:
        """Get docker compose version string, or None if not found."""
        try:
            return self.run(["compose", "version", "--short"], timeout=10).stdout.strip() or None
        except ComposeError:
            return None

    def _redact_text(self, text: str) -> str:
        """Replace known secrets in text with '***'."""
        redacted = text
        for secret in self._redact:
            redacted = redacted.replace(secret, "***")
        return redacted

    def _command(self, args: list[str]) -> list[str]:
        if args and args[0] in {"docker", "docker-compose"}:
            return [*args]
        return ["docker", *args]

    def _env(self, env: dict[str, str] | None) -> dict[str, str]:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        return merged

    def _command_error(
        self,
        command: list[str],
        returncode: int | None,
        stdout: str = "",
        stderr: str = "",
    ) -> DockerError | ComposeError:
        error_type = ComposeError if self._is_compose(command) else DockerError
        return error_type(tuple(command), returncode, self._redact_text(stderr), self._redact_text(stdout))

    @staticmethod
    def _is_compose(command: list[str]) -> bool:
        return bool(command) and (command[0] == "docker-compose" or (command[0] == "docker" and len(command) > 1 and command[1] == "compose"))

    @staticmethod
    def _decode(value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode(errors="replace")
        return value
