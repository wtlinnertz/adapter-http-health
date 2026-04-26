# AIEOS Adapter — verify.health via HTTP

Claims: `verify.health` at 1.0.0. Stdlib only.
Inputs: target_url + health_endpoint_configuration {paths, expected_status_codes}.
Output: findings.checks[] with per-endpoint pass/fail.
