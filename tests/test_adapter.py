"""Unit tests for adapter-http-health."""

from __future__ import annotations

import http.server
import threading
from contextlib import contextmanager

from aieos_adapter_http_health import HttpHealthAdapter


class _Handler(http.server.BaseHTTPRequestHandler):
    """Maps path -> response code via class-level dict set per test."""

    routes: dict[str, int] = {}

    def do_GET(self):
        code = self.routes.get(self.path, 404)
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):
        return


@contextmanager
def _server(routes: dict[str, int]):
    _Handler.routes = routes
    httpd = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_health_all_endpoints_pass():
    with _server({"/healthz": 200, "/readyz": 200, "/metrics": 200}) as url:
        result = HttpHealthAdapter().execute(
            {
                "target_url": url,
                "health_endpoint_configuration": {
                    "paths": ["/healthz", "/readyz", "/metrics"],
                    "expected_status_codes": [200, 200, 200],
                },
            }
        )
    assert result.exit_code == 0
    assert all(c["pass"] for c in result.findings["checks"])
    assert any("all-pass:True" in e for e in result.evidence)


def test_health_one_endpoint_fails():
    with _server({"/healthz": 200, "/readyz": 503}) as url:
        result = HttpHealthAdapter().execute(
            {
                "target_url": url,
                "health_endpoint_configuration": {"paths": ["/healthz", "/readyz"]},
            }
        )
    assert result.exit_code == 0  # adapter ran; validator decides
    checks = result.findings["checks"]
    assert checks[0]["pass"] is True
    assert checks[1]["pass"] is False
    assert checks[1]["observed_status"] == 503
    assert any("all-pass:False" in e for e in result.evidence)


def test_health_missing_inputs_returns_2():
    result = HttpHealthAdapter().execute({})
    assert result.exit_code == 2

    result = HttpHealthAdapter().execute({"target_url": "http://x"})
    assert result.exit_code == 2  # no paths


def test_health_default_expected_status_is_200():
    """If expected_status_codes is shorter than paths, missing entries default to 200."""
    with _server({"/a": 200, "/b": 200}) as url:
        result = HttpHealthAdapter().execute(
            {"target_url": url, "health_endpoint_configuration": {"paths": ["/a", "/b"]}}
        )
    assert all(c["pass"] for c in result.findings["checks"])


def test_health_expected_status_codes_per_path():
    """An endpoint that returns 503 with expected_status=503 passes."""
    with _server({"/maintenance": 503}) as url:
        result = HttpHealthAdapter().execute(
            {
                "target_url": url,
                "health_endpoint_configuration": {
                    "paths": ["/maintenance"],
                    "expected_status_codes": [503],
                },
            }
        )
    assert result.findings["checks"][0]["pass"] is True


def test_health_unreachable_endpoint_records_error():
    result = HttpHealthAdapter(timeout_seconds=0.5).execute(
        {
            "target_url": "http://127.0.0.1:1",  # nothing listens
            "health_endpoint_configuration": {"paths": ["/anything"]},
        }
    )
    check = result.findings["checks"][0]
    assert check["pass"] is False
    assert check["error"]  # non-empty
