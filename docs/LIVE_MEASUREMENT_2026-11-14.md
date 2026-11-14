# Rashi: first real paired measurement

2026-11-14, IST. Product remains partially built.

## Measured result

Same Kenari `glm-4-7-flash:free`, same HumanEval/0, /1, /2, same initial answer in both arms.

| Arm | Hidden-test passes | Logical calls |
|---|---:|---:|
| Bare model | 2/3 | 3 |
| Rashi prompt-visible repair | 2/3 | 4 |
| Independent-sampling control | 3/3 | 6 |

Signed Rashi lift: **0.0 percentage points**. Paired wins 0; losses 0.
Seven unique network calls because all arms share the three initial answers: three initial,
one repair, three independent samples. Total recorded network wait: 284.669 seconds.
No provider errors in this study. One initial answer was empty; its repair included markdown
fences despite the body-only contract. Those outputs were graded as returned, not cleaned up
or rerun for a better score. The independent sample passed that task.

This supports no claim of a benchmark improvement. Three ordered tasks are too few to infer
reliability, a representative score or statistical significance. This is not an official
HumanEval leaderboard result. The control beat the tested repair arm on this tiny sample.

## Method and evidence

- Predeclared tasks and denominator were kept. Max two logical attempts per enhanced/control arm.
- Selection and repair used only prompt-visible doctests and syntax execution. Hidden tests were
  final grades after candidate selection, never feedback for a repair or selection.
- Linux bwrap isolation preflight passed before model calls.
- Original outputs and errors were saved. Calls were resumed from local saved responses between
  bounded execution steps, not sampled again. JSON records exact samples, grades and call counts.
- Data SHA-256: `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef`.
- Upstream source commit: `b9453e8f1865df0a0057a1383767caa400acfbcf`, MIT license.
- Source: https://github.com/openai/human-eval?tab=MIT-1-ov-file

## Original goal run: failed before coding

The planned `bench_summary.py` goal did not reach implementation. First attempt recorded one
API timeout, then a cut-off draft, reviewer findings and an empty revision. It produced zero
usable checks. A second explicitly shorter spec attempt with a larger output budget still
ended in a truncated revision and zero usable checks. No coding agent ran and no DONE was claimed.
These attempts are separate from the seven-call paired study and were not benchmark successes.

The evidence points to model-output truncation/empty responses and weak spec-format adherence.
The gate refused coding instead of treating missing checks as success. Next work is a bounded
structured spec/output-completeness fix plus a new goal run, with this failure retained.

## What this does not prove

No whole-product readiness, market-readiness, 80-90% guarantee, full DSH real-model UI-to-goal,
installed coding-CLI compatibility, branded EXE/APK, or statistically supported lift.
Zero paid fallback was used.
