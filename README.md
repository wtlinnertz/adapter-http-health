# adapter-http-health

AIEOS adapter: `verify.health` via multi-endpoint HTTP probe. Stdlib only.
Probes one or more health endpoints; returns per-check pass/fail. The run
validator's `all_endpoints_healthy` criterion checks every entry passed.

```bash
pip install -e '.[dev]' && pytest
```
MIT.
