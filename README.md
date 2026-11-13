# Rashi Harness

Experimental multi-model coding harness. Status: **early prototype**. This README lists only what exists in the code today.

## What works now (tested, see `tests/`)
- `rashi/loop.py`: a verified loop. A task is DONE only when its check commands exit 0. The model's own claim of "done" is ignored. Protected files (specs, tests) are hash-checked every iteration and after the checks run; changing them fails the run. State is written to `PROGRESS.json`. Stops on max iterations or time.
- `rashi/fleet.py` + `rashi/orchestrate.py` + `rashi/build.py`: detects installed agent CLIs (Codex, Claude Code, OpenCode, Aider, Factory Droid, Gemini), tests readiness and prints fixes, then one press (`build.one_press`) specs, splits, and distributes tasks across ready agents - each task verified by the loop in its own subdirectory. See `docs/ORCHESTRATION.md`.
- `rashi/rules.py`: the ponytail (smallest complete change) and no-ai-slop rules, always consulted by the planner/coder/reviewer prompts.
- `rashi/llm_agent.py`: edit step through any OpenAI-compatible gateway. Free-tier gateways only (Coarena/paid is refused in code). Writes are confined to the work directory and cannot touch protected paths.
- `autonomous_loop_engine.py`: the older two-stage build + cross-review demo. Its approval gate now fails closed (error or missing field = not approved) and empty/refusal output is rejected.
- `rashi_cloud_runner.py`: cloud browser worker. Needs a bearer token, binds to localhost, and only fetches public http(s) URLs.
- `rakshex-core/`: Rust prototype of a daily spend breaker and model catalog. **The breaker is not connected to anything yet** and the websocket telemetry is demo data.

## Not built yet (roadmap)
Sandboxed code execution, repo map, rollback per step, multi-round model debate with voting, live war-room data, DeepSeek Harness plugin front end, Android app, voice, research agent, memory. Earlier drafts of this README claimed Redis checkpoints, Docker deployment, "20+ frontier models" and self-healing loops: those did not exist and were removed.

## Run it
```bash
pip install -r requirements-dev.txt
python -m pytest -q tests        # the test suite
python -m rashi fleet            # which agent CLIs are installed and ready
python -m rashi build "build X" workdir   # one press: spec -> approve -> distribute -> verify
python -m rashi warroom workdir  # live event stream UI on http://127.0.0.1:8765
```
`build` needs one free provider key in the environment (KENARI_API_KEY first) for spec drafting; the coding is done by the CLI agents `fleet` found ready.

## Keys
Copy `.env.example` to `.env` and fill it. Never commit keys; `tests/test_phase0.py` fails if a known key pattern appears in the tree.

## Models
Model IDs differ per gateway; list them with the gateway's `/v1/models` before use. Some IDs in older scripts (for example `...:free` suffixes) did not match the gateway lists on 2026-11-12. Manual live probes (including the ones that call paid endpoints) live in `probes/`; paid probes refuse to run unless `RASHI_ALLOW_PAID_PROBES=1`.

## License
MIT. See `LICENSE`.
