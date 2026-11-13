# Measure harness lift, do not promise it

2026-11-13. User goal: improve whatever model is brought to Rashi. 80-90% is an aspiration, not a result or guarantee. "Any model" requires an adapter that can call it; models unable to follow the completion interface can fail this study.

## Paired method now implemented

`rashi paired-bench --data /path/to/HumanEval.jsonl.gz --limit 3 --max-attempts 2 --control --out paired.json`

- Same model/provider callable, same pinned task subset, same initial completion for bare and Rashi arms.
- Bare arm: first completion, one final hidden-test grade.
- Rashi arm: prompt-visible doctest examples and syntax/execution status guide bounded repairs. No benchmark hidden-test body or outcome is used for repair, stopping or selection. One final hidden-test grade after selection.
- Independent control (optional): same maximum number of model calls as repair, independent completions and visible-example-only selection. Actual calls are recorded; early stopping can make actual use unequal. This is not called an equal-compute experiment.
- Fixed denominator; model errors remain failures. Record per-task wins and regressions, exact samples, calls, model/provider, elapsed time and dataset hash. Lift = (Rashi passes - bare passes) / total, in percentage points. It can be negative.
- Do not label this custom protocol official HumanEval pass@1/pass@k or compare a tiny ordered subset with full leaderboard percentages. Repeated runs, representative tasks and matched token/time budgets remain necessary before general claims.

Calibration only: canonical completions passed 3/3 in each arm (zero lift). Fake-model unit tests exercise repair/wins and fixed denominators but are not empirical model evidence. Real free-model A/B is queued after quota reset.

## Techniques vetted against primary sources

| Technique/source | Observed evidence and license | Rashi action |
|---|---|---|
| [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent/) | MIT, simple linear history/command execution and several sandbox environments. Its reported SWE-bench score belongs to its own models/setup, not Rashi. | Keep callable model interface and small execution adapters. Do not import its full dependency tree just for a repair loop. |
| [SWE-agent ACI](https://swe-agent.com/latest/background/aci/) and [paper](https://arxiv.org/html/2405.15793v3) | Documentation describes syntax guard, bounded viewers/search and concise command feedback. Paper ablations support interface importance in that setup. [Repo](https://github.com/SWE-agent/SWE-agent/blob/main/README.md) MIT. | Existing check feedback/repo map align with this; syntax/read guards need their own ablations, not assumed gains. |
| [Reflexion](https://github.com/noahshinn/reflexion/) | MIT repo, reflection from feedback and episodic memory. Published numbers are not transferable to Rashi. | Cheap bounded repair implemented independently using visible examples; current run memory exists, but full reflective memory is not claimed equivalent. |
| [Agentless](https://github.com/OpenAutoCoder/Agentless/) | MIT, localization -> repair -> validation; candidate selection using regression/reproduction tests. Full SWE-bench flow requires heavier environments. | Independent-sampling visible verifier control now; repo localization and official patch-validation jobs remain planned. |
| [Self-debugging limits](https://arxiv.org/html/2501.12793) | Primary paper warns about self-generated-test bias and hidden-oracle feedback confounds. | Official hidden tests never guide the implemented repair loop. Visible tests are imperfect; report regressions. |
| [EGM](https://github.com/google/elephant-goldfish-model) | Apache-2.0 source pattern previously inspected. Context-rich drafting, fresh reviews and explicit decisions. | Spec-first stays a product feature; not silently added to this first A/B. Later ablate spec-first separately to measure whether extra calls help. |

No non-commercial source code has been copied. Reading a non-commercial repository does not automatically authorize a commercial derivative. Prefer permissive sources; independently implement general published techniques without copying restricted code, assets or prompts, and review ambiguous rights before reuse.

## Next ablations

1. Bare vs bounded visible-feedback repair vs independent samples, same model/task IDs, actual calls disclosed.
2. Syntax guard and reflection as separate switches, with matched budgets.
3. EvalPlus stronger hidden tests after selecting candidates on visible tests only.
4. Aider Python edit tasks and SWE-style repository tasks for real software behavior; repo map/retrieval and spec-first ablations there, where project context exists.

These adapters and offline checks do not establish market readiness. Free-model run pending. No paid provider or rented evaluator has been used.
