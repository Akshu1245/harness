# Agent roles, model rules and routing (written before the code in rashi/roles.py, rashi/router.py)

## Principles
1. Tests and exit codes decide DONE. No model, router or reviewer decides it.
2. Free-tier providers only. Coarena and any paid endpoint are refused in code.
3. A reviewer never sees the author's conversation (fresh context).
4. Bug bounty work runs only against targets in an authorization record (see Bounty).
5. No user keys are shipped. Each user supplies their own, or a proxy holds them.

## Roles
| Role | Job | Sees | May write | Must not |
|---|---|---|---|---|
| planner (elephant) | Draft a spec with Goal, Files, Checks, Out of scope | project context, goal | spec file only | edit code |
| coder | Make the checks pass | spec, current files, failing output | unprotected files | touch tests or protected paths, add network calls to unlisted hosts |
| reviewer (goldfish) | Find unstated assumptions and bugs, JSON findings | spec or diff plus referenced files only | nothing | see planner/coder chat |
| security | Look for key leaks, injection, SSRF, unsafe shell | diff | nothing | run exploit code |
| bounty-scout | Recon and report for an authorized target | scope record, public responses | report file | send any request to a host outside scope, exploit, exfiltrate |
| router | Pick the role and model for a task | task text | decision log | decide DONE |

## Model rules (per model family)
- Strong coder models (gpt-class, claude-class on free tiers): coder, planner.
- Small or fast models: reviewer and security first pass only, never sole judge.
- A reviewer must use a different model from the coder when more than one is available.
- Model IDs come from a provider list-models probe, not from hardcoded names. A model missing from the probe is not used.
- A provider that returns 402/429 is skipped for the rest of the run and the event is logged.

## Router policy
1. Laya is the first-preference router. Its choice is used when its max probability is at least the calibrated threshold.
2. Otherwise, or if Laya is unavailable, deterministic keyword rules route the task.
3. Every decision is logged to JSONL: task, candidates, who decided (laya or rules), probabilities, chosen role, later outcome.
4. Calibration compares Laya, rules and the majority-class baseline on our logged outcomes. If Laya does not beat rules on our data, the report says so and the threshold is raised until it only handles cases where it does.
5. Evidence: arXiv 2610.02267 reports that both Laya and Jev fail at zero-shot model routing and that Laya is sensitive to option order. So Laya's routing is measured here, not trusted.

## Bounty rules
Authorization record = program name, URL of the program policy, in-scope hosts, out-of-scope hosts, rules (rate limit, no DoS), date. Deny by default. Check every URL before every request. Out-of-scope beats in-scope. Wildcards match subdomains only. No record, no run.
