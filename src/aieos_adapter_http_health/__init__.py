"""AIEOS adapter: verify.health via multi-endpoint HTTP probe.

Probes a set of health endpoints; records per-check pass/fail in findings.
The run validator's `all_endpoints_healthy` criterion checks every entry
passed.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from time import perf_counter
from typing import Any

__version__ = "1.0.0"


@dataclass
class AdapterResult:
    findings: dict[str, Any] | None
    evidence: list[str]
    exit_code: int


class HttpHealthAdapter:
    """Probes one or more endpoints, records per-check results.

    health_endpoint_configuration shape:
        paths:                 list[str]            — paths relative to target_url
        expected_status_codes: list[int] (optional) — per-path expected codes;
                                                     default [200] applied to all
    """

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._timeout = timeout_seconds

    def execute(self, inputs: dict[str, Any]) -> AdapterResult:
        target_url = inputs.get("target_url", "")
        config = inputs.get("health_endpoint_configuration") or {}
        paths = list(config.get("paths") or [])
        expected = list(config.get("expected_status_codes") or [])

        if not target_url or not paths:
            return AdapterResult(
                findings=None,
                evidence=["exit-code:2", "stderr:target_url or paths missing"],
                exit_code=2,
            )

        # Pad expected codes with 200 if shorter than paths.
        while len(expected) < len(paths):
            expected.append(200)

        checks: list[dict[str, Any]] = []
        for path, exp_code in zip(paths, expected, strict=False):
            check = _probe(target_url, path, int(exp_code), self._timeout)
            checks.append(check)

        all_pass = all(c["pass"] for c in checks)
        return AdapterResult(
            findings={"checks": checks},
            evidence=[
                f"per-check-results:{len(checks)}",
                f"all-pass:{all_pass}",
                f"exit-code:{0 if all_pass else 0}",  # exit 0 always; the run validator decides
            ],
            exit_code=0,
        )


def _probe(
    target_url: str,
    path: str,
    expected_status: int,
    timeout: float,
) -> dict[str, Any]:
    url = target_url.rstrip("/") + "/" + path.lstrip("/")
    request = urllib.request.Request(url, method="GET")
    observed: int | None = None
    latency_ms: int = 0
    error: str = ""
    try:
        t0 = perf_counter()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            observed = response.status
        latency_ms = int((perf_counter() - t0) * 1000)
    except urllib.error.HTTPError as exc:
        observed = exc.code
        latency_ms = 0
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        observed = None
        error = f"{type(exc).__name__}: {exc}"
    return {
        "path": path,
        "expected_status": expected_status,
        "observed_status": observed if observed is not None else 0,
        "latency_ms": latency_ms,
        "pass": observed == expected_status,
        "error": error,
    }
