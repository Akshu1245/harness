# Live probes (manual only)

These scripts call real gateways. They are NOT part of the test suite (`pytest` only collects
`tests/`, see `pytest.ini`) and nothing on the automatic path imports them.

- `all_models_live.py` calls PAID endpoints (Coarena tie-breaker, paid Claude). It refuses to run
  unless `RASHI_ALLOW_PAID_PROBES=1` is set. Zero-spend rule: do not set it without his say-so.
- The rest (`explabs_free.py`, `gateway_explabs.py`, `all_screenshot_models.py`,
  `verify_all_gateways.py`, `cloud_runner_health_check.py`) target free models but still consume
  free-tier daily rate limits, which the SpendGate counts.

They were renamed from their old `test_*.py` names at the repo root so a bare `pytest` run can
never collect them by accident.
