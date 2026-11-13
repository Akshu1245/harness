# Public benchmark plan - 2026-11-13

The product is partially built. A runner is not a benchmark result. Current proof is evaluator calibration only, not a model score or leaderboard submission.

## Choose by what we need to prove

| Benchmark | Observed license / adoption snapshot | Fit and weight | Decision |
|---|---|---|---|
| [HumanEval](https://github.com/openai/human-eval?tab=MIT-1-ov-file) | MIT repo including checked-in data; 3,426 stars via GitHub API | Short Python function completion, small data, stdlib grading possible. Not repo-scale agent proof; old/public tasks may be in training data. Upstream warns to isolate generated code. | Wired a 3-task custom subset adapter now, not the official harness. |
| [EvalPlus](https://github.com/evalplus/evalplus/) | Apache-2.0 code; 1,838 stars. Dataset license must be checked separately before bundling. | HumanEval+/MBPP+ add stronger tests. Good next quality layer. Can evaluate generated samples offline after fetching assets; keep package/images outside product runtime. | Next external evaluator after basic subset live proof. No claim of EvalPlus compatibility yet. |
| [Aider polyglot](https://github.com/Aider-AI/polyglot-benchmark/) and [harness](https://github.com/Aider-AI/aider/blob/main/benchmark/README.md) | Exercises repo 228 stars; root API license null. README sends licensing to each Exercism track. Aider itself Apache-2.0, 50,109 stars. Do not equate code license with exercise license. | 225 exercises across six languages, file-editing plus test feedback closer to Rashi than function completion. Official harness recommends Docker; language toolchains add weight. | Python-track subset later, after track attribution/license audit; no dataset vendored now. |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench/blob/main/README.md) | MIT harness, 6,181 stars; target repositories retain their licenses | Real issue-to-patch proof; Verified has 500 reviewed tasks, Lite is smaller. [Harness docs](https://github.com/SWE-bench/SWE-bench/blob/main/docs/reference/harness.md) recommend 120GB free disk, 16GB RAM, 8+ cores and Docker. | Official external evaluation job later. Do not embed or silently rent infrastructure. |
| [LiveCodeBench](https://github.com/LiveCodeBench/LiveCodeBench/) | MIT code, 974 stars. Contest problem rights and dataset conditions are separate, not cleared by that license. | Fresh contest tasks and date windows help contamination analysis; algorithms, not full-product completion. Data/harness dependencies and safe execution required. | Deferred pending dataset-rights review and pinned release. |
| [TestSuiteBench](https://github.com/eth-sri/testsuitebench) | MIT code, 4 stars from live API. Low stars do not erase primary-paper evidence. Reference binaries/tests/mutants come from separate datasets and originating projects. | 165 CLI apps, validity plus mutant kills, directly tests whether our checks are strong. Linux amd64 Docker; optional complete offline cache about 100GB per docs. | Adopt validity-before-mutation scoring principle now; full public run later in external evaluation environment. Existing local hand-written mutants are NOT a TestSuiteBench score. |
| [BigCodeBench](https://github.com/bigcode-project/bigcodebench) | Apache-2.0 code, 517 stars. Dataset card/license needs separate clearance before redistribution. | Practical library-heavy Python; useful beyond puzzles, but dependencies and images are heavier. | External optional evaluator later, not a runtime dependency. |
| [Terminal-Bench](https://github.com/harbor-framework/terminal-bench) | Apache-2.0 repo, 1,047 stars; individual task assets need checking | Broad terminal agent tasks. Current project uses Harbor and recommends repeated oracle checks in the sandbox. Images/runtime provisioning are heavier than this first adapter. | Later agent-level acceptance suite using the official pinned task release. No paid sandbox setup. |

Stars are a dated discovery signal, not proof of correctness or security. Counts above were read from each repository's live GitHub API on 2026-11-13 and may change. Missing dataset clearance means "do not redistribute yet", not a claim that use is forbidden.

## What was built and actually checked

`rashi public-bench` loads a caller-supplied local HumanEval JSONL(.gz), selects the first N tasks deterministically, accepts one completion per task or generates one with the configured free default model, and writes exact task IDs, data SHA-256, denominator and per-task outcomes. Missing answers fail; duplicates are rejected. Test cases and canonical solutions are not passed to generation. Generated samples are saved for replay.

The evaluator requires bwrap. It uses a fresh root with runtime directories and a disposable grader directory, clears environment variables, disables network, uses Python isolated/no-site mode and CPU/memory/file/process limits. Missing or broken isolation stops the run. This is defense in depth on a disposable host, not a tamper-proof evaluator or a guarantee against kernel exploits. Do not run hostile code on a valuable host.

Observed source checkout: `openai/human-eval` commit `b9453e8f1865df0a0057a1383767caa400acfbcf`.
Observed compressed dataset SHA-256: `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef`.
Observed IDs: `HumanEval/0`, `HumanEval/1`, `HumanEval/2`.
Calibration: canonical solutions passed 3/3; intentionally broken completions passed 0/3. NOT a Rashi model result. Free-model generation remains unmeasured until the existing free quota resets. A three-task selected subset cannot establish general coding ability or be compared directly with official full-set leaderboard scores.

Example, after separately obtaining the upstream data:

```sh
rashi public-bench --data /path/to/HumanEval.jsonl.gz --limit 3 --self-test --out calibration.json
rashi public-bench --data /path/to/HumanEval.jsonl.gz --limit 3 --samples samples.jsonl --out measured.json
# Explicit model use, free configured default only:
rashi public-bench --data /path/to/HumanEval.jsonl.gz --limit 3 --generate --out measured.json
```

## Other OSS worth reusing, without bloating the runtime

- [mutmut](https://github.com/boxed/mutmut/) is BSD-3-Clause and supports incremental Python mutation testing. Requires fork support (Windows via WSL). Good optional development-only check for our rollback/safety tests. Read its actual license before copying code; do not apply mutants to a dirty tree. Planned, not installed or benchmarked here.
- [Hypothesis](https://github.com/hypothesisworks/hypothesis) provides generated inputs and shrinking, a good fit for path confinement, task-ID validation, parser and resume-state properties. GitHub API reports a nonstandard license identifier; full file-level licensing still needs inspection before vendoring. Candidate only, not bundled or claimed verified.
- Keep the public evaluator and optional benchmark packages separate from the normal install. Prefer official grading harnesses for future public scores rather than rewriting their metrics.

## Sequence and remaining gates

1. Finish safety hardening (rollback deletions/containment and resume spec identity/feedback); keep DSH/MCP builds disabled until approval handshake exists.
2. Run the three-task prompt-only free-model subset after quota reset; retain samples and failures as evidence. Label it a custom subset, not pass@k or a leaderboard result.
3. Add EvalPlus external sample scoring and a license-cleared Aider Python subset.
4. When local Docker/resources are available, run official SWE-bench Lite/Verified and TestSuiteBench oracle checks before model evaluations. No infrastructure purchases without approval.
5. Add contamination/date-window analysis and Terminal-Bench only when exact releases, task licenses and infrastructure are verified.

Independent landscape source for taxonomy (not used to settle licenses): https://evalsreview.com/best/coding-benchmarks . Primary academic explanation: https://www.sri.inf.ethz.ch/publications/egashira2026testsuitebench . All practical decisions above use the linked first-party READMEs and live repository metadata.
