# Rashi Harness

Experimental multi-model coding harness. Status: **early prototype**. This README lists only what exists in the code today.

## What works now (tested, see `tests/`)
- `rashi/loop.py`: a verified loop. A task is DONE only when its check commands exit 0. The model's own claim of "done" is ignored. Protected files (specs, tests) are hash-checked every iteration and after the checks run; changing them fails the run. State is written to `PROGRESS.json`; an unfinished run can resume only when goal/checks/protected-path identity and protected content match, with retained failure feedback. A regression can restore modified/deleted files and remove additions from a bounded per-step stash. Incomplete recovery stops; rollback rejects symlink paths, but is not race-proof against hostile concurrent processes. Stops on max iterations or time. Every run writes what happened (done/rollback/stall) to `.rashi/memory.jsonl` and the next brainstorm/spec in that workdir reads it back as context. Checks can run sandboxed (bwrap: read-only system, writable workdir, no network) with `sandbox: True` or RASHI_SANDBOX=1.
- `rashi/fleet.py` + `rashi/orchestrate.py` + `rashi/build.py`: detects installed agent CLIs (Codex, Claude Code, OpenCode, Aider, Factory Droid, Gemini), tests readiness and prints fixes, then one press (`build.one_press`) specs, splits, and distributes tasks across ready agents - each task verified by the loop in its own subdirectory. See `docs/ORCHESTRATION.md`.
- `rashi/rules.py`: the ponytail (smallest complete change) and no-ai-slop rules, always consulted by the planner/coder/reviewer prompts.
- `rashi/llm_agent.py`: edit step through any OpenAI-compatible gateway. Free-tier gateways only by default; a paid model on your own key is an explicit opt-in (`RASHI_ALLOW_PAID=1` / `allow_paid=True`), refused otherwise. Writes are confined to the work directory and cannot touch protected paths.
- `rashi/intake.py` (`rashi ask "idea"`): paste an idea refined elsewhere, get ALL clarifying questions in one numbered multiple-choice batch; answer inline (`--answers`) or copy the batch into your own AI and bring answers back.
- Guard rails adapted from the DeepSeek Harness source (patterns reimplemented, no code copied): repeat/no-progress loop warning, per-check timeouts, 429 retry with backoff, read-before-edit (refuses to clobber a file changed since the model saw it), spill files for oversized check output, and RASHI_RECORD=1 run recording with keyless replay (`rashi/replay.py`).
- Never-lie rule (`rashi/rules.py` NEVER_LIE): no prompt in the harness may claim done/complete unless checks exited 0; partial work is reported as partial. Statuses are `DONE_VERIFIED` only on exit codes, else `INCOMPLETE`/the failure name.
- `autonomous_loop_engine.py`: the older two-stage build + cross-review demo. Its approval gate now fails closed (error or missing field = not approved) and empty/refusal output is rejected.
- `rashi_cloud_runner.py`: cloud browser worker. Needs a bearer token, binds to localhost, and only fetches public http(s) URLs.
- `rakshex-core/`: Rust prototype of a daily spend breaker and model catalog. **The breaker is not connected to anything yet** and the websocket telemetry is demo data.

## Not built yet (roadmap)
Sandboxed code execution, repo map, rollback per step, multi-round model debate with voting, live war-room data, DeepSeek Harness plugin front end, Android app, voice, research agent, memory. Earlier drafts of this README claimed Redis checkpoints, Docker deployment, "20+ frontier models" and self-healing loops: those did not exist and were removed.

## Install and run it
```bash
pip install .                    # or: pip install git+https://github.com/Akshu1245/harness
rashi fleet                      # which agent CLIs are ready on this machine
KENARI_API_KEY=... rashi bench   # live benchmark on a free model (free gateways only)
rashi ask "idea"                 # one batch of clarifying questions before a build
rashi warroom /tmp/rashi-bench   # live event-stream UI for a run directory
rashi drift spec.md .              # EGM drift report: spec paths missing from the code (exit 1 on drift)
rashi council "question"          # debate + vote across configured free gateways (advisory)
rashi research "topic"            # most-starred OSS for a topic, GitHub API, keyless (rashi build --research feeds it into the brief)
rashi mcp                         # MCP stdio server: agent CLIs call rashi tools directly (no dependencies)
```
Develop from a clone:
```bash
pip install -r requirements-dev.txt
python -m pytest -q tests        # the test suite
python -m rashi fleet            # which agent CLIs are installed and ready
python -m rashi build "build X" workdir   # one press: spec -> approve -> distribute -> verify
python -m rashi warroom workdir  # live event stream UI on http://127.0.0.1:8765
python -m rashi drift spec.md workdir   # spec-vs-code drift report, no key needed
```
`build` needs one free provider key in the environment (KENARI_API_KEY first) for spec drafting; the coding is done by the CLI agents `fleet` found ready.

## Keys
Copy `.env.example` to `.env` and fill it. Never commit keys; `tests/test_phase0.py` fails if a known key pattern appears in the tree.

## Models
Model IDs differ per gateway; list them with the gateway's `/v1/models` before use. Some IDs in older scripts (for example `...:free` suffixes) did not match the gateway lists on 2026-11-12. Manual live probes (including the ones that call paid endpoints) live in `probes/`; paid probes refuse to run unless `RASHI_ALLOW_PAID_PROBES=1`.

## License
MIT. See `LICENSE`.

## Verification limits

The product is partially built. DSH and MCP now have exact-generated-plan approval handshakes, tested with local deterministic agents. DSH uses native one-shot approval; MCP requires client form elicitation and refuses unsupported clients. Neither has a full real-model UI-to-build proof. CLI-agent invocation templates remain unverified against real installations. Council has offline fake-member tests, not a verified 16-model run. Research finds candidates; it does not vet them. Optional bwrap applies to checks only, is not a secrets-isolation boundary, and fails closed when requested but unavailable. Tracing is local JSONL, not hosted telemetry. See docs/GAPS_FOUND.md for current corrections.

## Public benchmark adapter

`rashi public-bench --data /path/to/HumanEval.jsonl.gz --limit 3 --self-test --out calibration.json` runs isolated evaluator calibration, not a model benchmark. `--samples FILE` grades one completion per task; `--generate` explicitly uses the configured free default model and saves samples. Requires Linux bwrap; no unsandboxed fallback. This custom subset is not an official leaderboard score or proof of whole-product readiness. See [the vetted benchmark plan](docs/PUBLIC_BENCHMARKS.md).
