from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from .docker import DockerAdapter
from .errors import ComposeError
from .errors import SuperclawCtlError


@dataclass(slots=True)
class ContainerInfo:
    name: str
    service: str
    state: str
    health: str
    ports: str
    image: str
    created: str


class ComposeProject:
    """Manages a Docker Compose project."""

    def __init__(
        self,
        adapter: DockerAdapter,
        compose_files: list[Path],
        project_name: str = "superclaw",
        env: dict[str, str] | None = None,
    ):
        self._adapter = adapter
        self._compose_files = compose_files
        self._project_name = project_name
        self._env = dict(env or {})

    def up(self, *, services: list[str] | None = None, detach: bool = True) -> None:
        """Start services with output rendered directly by Docker.

        With ``depends_on: condition: service_healthy`` in the compose file,
        the compose process blocks until all health-check dependencies are
        satisfied (which can take several minutes for vLLM).  Output is
        passed through to the terminal so Docker's native progress rendering
        (build layers, pull progress, health waits) displays correctly.
        """
        args = [*self._compose_args(), "up"]
        if detach:
            args.append("-d")
        args.extend(services or [])
        self._adapter.passthrough(args, env=self._env)

    def down(self, *, volumes: bool = False) -> None:
        """Stop and remove containers."""
        args = [*self._compose_args(), "down"]
        if volumes:
            args.append("--volumes")
        self._adapter.run(args, env=self._env)

    def restart(self, services: list[str] | None = None) -> None:
        """Restart services."""
        self._adapter.run([*self._compose_args(), "restart", *(services or [])], env=self._env)

    def ps(self) -> list[ContainerInfo]:
        """List containers with status, using --format json."""
        payload = self._adapter.run_json([*self._compose_args(), "ps", "--format", "json"], env=self._env)
        entries = payload if isinstance(payload, list) else [payload]
        if not all(isinstance(item, dict) for item in entries):
            raise ComposeError(tuple(["docker", *self._compose_args(), "ps", "--format", "json"]), None, stderr="unexpected compose ps payload")
        return [self._container_from_dict(item) for item in entries]

    def pull(self, services: list[str] | None = None) -> None:
        """Pull images for services (output rendered directly by Docker)."""
        self._adapter.passthrough([*self._compose_args(), "pull", *(services or [])], env=self._env)

    def logs(self, service: str | None = None, *, follow: bool = False, tail: int | None = None) -> Generator[str, None, None] | str:
        """Get or follow logs."""
        args = [*self._compose_args(), "logs"]
        if follow:
            args.append("--follow")
        if tail is not None:
            args.extend(["--tail", str(tail)])
        if service:
            args.append(service)
        if follow:
            return self._adapter.stream(args, env=self._env)
        return self._adapter.run(args, env=self._env).stdout

    def render_config(self) -> str:
        """Render resolved compose config."""
        return self._adapter.run([*self._compose_args(), "config"], env=self._env).stdout

    def running_project_names(self) -> list[str]:
        """Return other running Compose project names on the host."""
        try:
            payload = self._adapter.run_json(["compose", "ls", "--format", "json"], env=self._env)
        except SuperclawCtlError:
            return []

        entries = payload if isinstance(payload, list) else [payload]
        names: list[str] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            name = str(item.get("Name") or "").strip()
            status = str(item.get("Status") or "").lower()
            if name and status.startswith("running"):
                names.append(name)
        return [name for name in names if name != self._project_name]

    def _compose_args(self) -> list[str]:
        """Build base docker compose args with -f flags and -p project."""
        args = ["compose"]
        for compose_file in self._compose_files:
            args.extend(["-f", str(compose_file)])
        args.extend(["-p", self._project_name])
        return args

    def _container_from_dict(self, payload: dict[str, object]) -> ContainerInfo:
        status = str(payload.get("Status") or "")
        return ContainerInfo(
            name=str(payload.get("Name") or payload.get("Names") or ""),
            service=str(payload.get("Service") or ""),
            state=str(payload.get("State") or status.split(" ", 1)[0].lower() or "unknown"),
            health=str(payload.get("Health") or self._health_from_status(status)),
            ports=self._format_ports(payload.get("Publishers") or payload.get("Ports") or ""),
            image=str(payload.get("Image") or ""),
            created=str(payload.get("CreatedAt") or payload.get("Created") or ""),
        )

    @staticmethod
    def _health_from_status(status: str) -> str:
        lowered = status.lower()
        for health in ("healthy", "unhealthy", "starting"):
            if health in lowered:
                return health
        return "none"

    @staticmethod
    def _format_ports(value: object) -> str:
        if isinstance(value, str):
            return value
        if not isinstance(value, list):
            return ""
        parts: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            host_ip = item.get("URL") or item.get("HostIp") or ""
            published = item.get("PublishedPort")
            target = item.get("TargetPort")
            protocol = item.get("Protocol") or "tcp"
            if published and target:
                prefix = f"{host_ip}:" if host_ip else ""
                parts.append(f"{prefix}{published}->{target}/{protocol}")
        return ", ".join(parts)
