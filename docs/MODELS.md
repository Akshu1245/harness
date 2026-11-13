# Free model table

Zero-spend rule: only models listed here may be used automatically. Regenerate the Kenari
section with: `python -m rashi.model_table /path/to/fresh/kenari-models.json`.

## Verified in the verified loop (exit-code DONE_VERIFIED, live)

| provider | model | task | date (IST) | wall time |
|---|---|---|---|---|
| ExpLabs | gpt-6-luna | slugify utility | 2026-11-12 | ~2s/call |
| Kenari | glm-4-7-flash:free | write add() function | 2026-11-13 | 74.7s, 1 iter |
| Kenari | glm-4-7-flash:free | one-press build flow (spec gate -> task split -> distribute -> loop), add() in math_utils.py | 2026-11-13 | 1 iter |
| Kenari | glm-4-7-flash:free | benchmark pass: 3 fixed tasks (fib module, CLI tool, stdin-JSON tool), `python -m rashi bench` | 2026-11-13 | 3/3 DONE_VERIFIED, all iter 1, 5-14s each |

Benchmark honesty note: bench-fib first shipped with a pytest-dependent check and failed
STOPPED_MAX_ITERS even though the model wrote correct code - the loop ran `python`, which has
no pytest in a bare environment. The loop was right to refuse DONE; the check was wrong.
Checks in rashi/data/tasks.json (packaged; was benchmarks/tasks.json) now use only stdlib assumptions. Raw rows: benchmarks/results.jsonl.

Lesson from the one-press live run: the flash model drafted a clean spec with three valid checks
and wrote correct code first try, but its JSON-only replies (goldfish findings, task split) came
back unparsable once each; both fallbacks (high-finding record, single-task split) absorbed it.
Both now retry once with an explicit JSON-only reminder before falling back (same commit series).

Lesson from live runs: prefer flash-class (non-reasoning) models for loop iterations; reasoning
models blew the 90s client timeout against Kenari's 5 rpm free tier. Use reasoning models only
where their output is the product (e.g. spec drafting), with a longer timeout.

## Kenari free chat models (live probe 2026-11-13 IST, 106 models total)

<!-- probe-generated from /tmp/kenari_models.json; do not hand-edit -->
| model | tool calling | reasoning | context |
|---|---|---|---|
| hy4:free | yes | yes | 1,048,576 |
| longcat-2-5:free | yes | no | 1,048,576 |
| ernie-5-5-flash-preview:free | yes | yes | 1,024,000 |
| nemotron-3-5-lightning:free | yes | yes | 1,000,000 |
| nemotron-3-5-super-vl:free | yes | yes | 1,000,000 |
| nemotron-3-ultra-550b-a55b:free | yes | yes | 1,000,000 |
| qwen3-8-omni-flash:free | yes | yes | 1,000,000 |
| solar-mini4:free | yes | yes | 524,288 |
| dots-3-note-preview:free | yes | yes | 512,000 |
| flint-v1-0:free | yes | yes | 262,144 |
| laguna-xs-2-1:free | yes | yes | 262,144 |
| lfm-3-1-7b:free | yes | yes | 262,144 |
| qwen3-5-397b-a17b:free | yes | yes | 262,144 |
| qwen3-6-27b:free | yes | yes | 262,144 |
| xing4-0-29b-a4b:free | no | no | 262,144 |
| qwen3-8-27b:free | yes | yes | 262,000 |
| nemotron-3-nano-omni-30b-a3b-reasoning:free | yes | yes | 256,000 |
| north-mini-code:free | yes | yes | 256,000 |
| glm-4-7-flash:free | yes | yes | 200,000 |
| hy3:free | yes | yes | 196,608 |
| llama-3-3-70b-instruct:free | yes | no | 131,072 |
| muse-glimmer-30b:free | yes | yes | 131,072 |
| glm-4-6v-flash:free | yes | no | 128,000 |


Honesty note (2026-11-13, later): the benchmark checks were STRENGTHENED after the first live pass - mutation testing (each task now ships wrong-but-plausible mutants its checks must kill) exposed four weak checks (single-input sum, single-name greet, self-attesting test file, hardcoded bump2). The 3/3 numbers above predate the stronger suite; the next live pass re-measures against it.
