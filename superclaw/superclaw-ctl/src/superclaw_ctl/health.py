from __future__ import annotations

"""HTTP health probes with retry and timeout helpers."""

from collections.abc import Callable
from typing import Any
from dataclasses import dataclass
import json
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
    body = response.text
    healthy = 200 <= response.status_code < 300
    error = ""
    if not healthy:
        body_preview = body[:300].strip().replace("\n", " ")
        error = f"HTTP {response.status_code}"
        if body_preview:
            error = f"{error}: {body_preview}"
    return HealthStatus(
        service=service,
        healthy=healthy,
        status_code=response.status_code,
        response_body=body,
        error=error,
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


def wait_for_router_models(
    url: str,
    *,
    expected_models: tuple[str, ...],
    headers: dict[str, str] | None = None,
    timeout: float = 300,
    interval: float = 5.0,
    on_retry: Callable[[int, float], Any] | None = None,
) -> HealthStatus:
    """Poll router /v1/models until all expected models are listed."""
    started = time.monotonic()
    attempt = 0
    last = HealthStatus(service="vLLM router", healthy=False)
    while True:
        elapsed = time.monotonic() - started
        remaining = timeout - elapsed
        if remaining <= 0:
            if not last.error:
                missing = ", ".join(expected_models)
                last.error = f"Timed out after {timeout:.1f}s waiting for router models: {missing}."
            return last

        attempt += 1
        last = probe_endpoint(url, headers=headers, timeout=min(interval, remaining))
        last.service = "vLLM router"

        if last.healthy:
            missing = [model for model in expected_models if not _router_body_contains_model(last.response_body, model)]
            if not missing:
                return last
            last.healthy = False
            last.error = f"Router is healthy but missing models: {', '.join(missing)}."

        elapsed = time.monotonic() - started
        if elapsed >= timeout:
            if not last.error:
                last.error = f"Timed out after {timeout:.1f}s waiting for router models."
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


def _extract_model_ids(body: str) -> set[str]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return set()

    items: list[Any]
    if isinstance(payload, dict):
        data = payload.get("data", [])
        items = data if isinstance(data, list) else []
    elif isinstance(payload, list):
        items = payload
    else:
        return set()

    model_ids: set[str] = set()
    for item in items:
        if isinstance(item, str):
            model_ids.add(item)
            continue
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("model_id") or item.get("name")
            if isinstance(model_id, str) and model_id:
                model_ids.add(model_id)
    return model_ids


def _router_body_contains_model(body: str, expected_model: str) -> bool:
    expected = expected_model.strip().lower()
    if not expected:
        return False

    model_ids = _extract_model_ids(body)
    for model_id in model_ids:
        lowered = model_id.lower()
        if lowered == expected or expected in lowered:
            return True

    # Fallback to substring check, mirroring compose healthcheck grep behavior.
    return expected in body.lower()
