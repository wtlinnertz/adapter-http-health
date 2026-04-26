# MAPPING — adapter-http-health

Probes each path in health_endpoint_configuration.paths against target_url.
expected_status_codes (optional) maps 1:1 to paths; shorter lists default to
200 for missing entries.

Per-check fields:
- path, expected_status, observed_status, latency_ms, pass, error

The run validator's all_endpoints_healthy criterion asserts every check has
pass=true.

Adapter exit code is 0 whenever the probes ran (regardless of outcomes);
exit_code 2 on missing target_url or missing paths.
