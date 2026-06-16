from __future__ import annotations

"""HTTP health probes with retry and timeout helpers."""

from collections.abc import Callable
from typing import Any
from dataclasses import dataclass
import time
from urllib.parse import urlparse

import httpx


@dataclass(slots=True)
class HealthStatus:
    """Result of probing a service health endpoint."""

    service: str
    healthy: bool
    status_code: int | None = None
    response_body: str = ""
    error: str = ""
    latency_ms: float = 0


def probe_endpoint(url: str, *, headers: dict[str, str] | None = None, timeout: float = 5.0) -> HealthStatus:
    """Single health probe to a URL."""
    service = urlparse(url).netloc or url
    started = time.perf_counter()
    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
    except httpx.HTTPError as exc:
        return HealthStatus(service=service, healthy=False, error=str(exc), latency_ms=(time.perf_counter() - started) * 1000)
    latency_ms = (time.perf_counter() - started) * 1000
    body = response.text[:1000]
    return HealthStatus(
        service=service,
        healthy=200 <= response.status_code < 300,
        status_code=response.status_code,
        response_body=body,
        latency_ms=latency_ms,
    )


def wait_for_healthy(
    url: str,
    *,
    service_name: str = "",
    headers: dict[str, str] | None = None,
    timeout: float = 300,
    interval: float = 5.0,
    on_retry: Callable[[int, float], Any] | None = None,
) -> HealthStatus:
    """Poll until healthy or timeout. Calls on_retry(attempt, elapsed) each iteration."""
    started = time.monotonic()
    attempt = 0
    last = HealthStatus(service=service_name or (urlparse(url).netloc or url), healthy=False)
    while True:
        elapsed = time.monotonic() - started
        remaining = timeout - elapsed
        if remaining <= 0:
            last.error = last.error or f"Timed out after {timeout:.1f}s waiting for {last.service}."
            return last
        attempt += 1
        last = probe_endpoint(url, headers=headers, timeout=min(interval, remaining))
        if service_name:
            last.service = service_name
        if last.healthy:
            return last
        elapsed = time.monotonic() - started
        if elapsed >= timeout:
            last.error = last.error or f"Timed out after {timeout:.1f}s waiting for {last.service}."
            return last
        if on_retry is not None:
            on_retry(attempt, elapsed)
        time.sleep(min(interval, max(timeout - elapsed, 0)))


def check_vllm_health(host: str = "127.0.0.1", port: int = 18103, api_key: str = "") -> HealthStatus:
    """Check vLLM /v1/models endpoint."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    status = probe_endpoint(f"http://{host}:{port}/v1/models", headers=headers)
    status.service = "vllm"
    return status


def check_router_health(host: str = "127.0.0.1", port: int = 8080, api_key: str = "") -> HealthStatus:
    """Check model service router /v1/models endpoint."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    status = probe_endpoint(f"http://{host}:{port}/v1/models", headers=headers, timeout=3.0)
    status.service = "model service router"
    return status
