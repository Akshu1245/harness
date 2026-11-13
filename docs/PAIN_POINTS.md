# What real users complain about in AI coding tools (research pass 2026-11-13)

Sources: GitHub issues, Reddit, Hacker News. Every pain below links the thread it came
from. "Observed" = stated by users in the thread. "Inferred" = our reading of what it
means for this harness. No numbers here are ours; quoted figures are the sources' own.

## Ranked pains

### 1. Unpredictable cost and token burn
- Observed: HN Pain Radar aggregates 55 mentions from 53 distinct people over the last
  year for "unpredictable / high token and subscription costs", peaking at 9/month in
  early 2026 (https://hnpainradar.fly.dev/problems/cost).
- Observed: a Cursor user reports stuck subagents and a runaway rg.exe subprocess
  "wasted 300M tokens in one day for 2k edited lines, 90% [of the] $200 plan in 5 days"
  (https://www.reddit.com/r/cursor/comments/1vkx2jo/).
- Observed: HN thread on GitHub Copilot metered billing, "Angry devs vow to flee"
  (https://news.ycombinator.com/item?id=48364983); Windsurf users leaving over pricing
  and quota opacity (https://www.reddit.com/r/windsurf/comments/1s0v3nd/,
  https://www.reddit.com/r/windsurf/comments/1rysksi/).
- Observed: retry/flaky cost multiplies the real price of a task: "the retry and flaky
  cost will be many times bigger than the average token cost" (HN Pain Radar, sinuhe69).

### 2. Agents stop when nobody is watching
- Observed: claude-code issue #84002 documents an agent that "cannot hold a check-in
  every 20 minutes", stopped overnight for 5h31m against a standing order, and a worker
  sat in an infinite wait on a dead producer for 90 minutes with nothing alarming. The
  agent's own diagnosis: "I only act when something gives me a turn... the gap is
  structural." (https://github.com/anthropics/claude-code/issues/84002)
- Observed: same shape on HN: "it worked for about 20 minutes after I went to bed, and
  decided that it would stop" on overnight task lists (HN Pain Radar, spacedcowboy).
- Observed: a scheduled watcher missed four CRITICAL pages during a live trading window
  because "it was in a turn, finished the turn, and stopped existing" (#84002, §2).

### 3. False completion: status that looks like work but certifies nothing
- Observed: #84002 again - a mechanically-forced heartbeat produced fresh-timestamped
  check-ins whose content was stale, unread, and invented a blocker: "You can
  mechanically force an agent to write a file on a schedule. You cannot mechanically
  force the file to be true." Also: "Idleness that reports as progress."
- Inferred: this is the deepest pain and the least addressed by existing tools. DONE
  claims, status dashboards, and "progress" are all suspect unless tied to an external
  check the model cannot influence.

### 4. Breaks unrelated parts of the system; subtle destructive drift
- Observed: HN "AI coding is a nightmare" thread - hyper-defensive try/except that
  hides failures, duplicate functions reinvented per session, and "hyper-focuses on the
  current task... couldn't care less if its changes break other parts of the system"
  (https://news.ycombinator.com/item?id=48770319). The accepted mitigations in that
  thread: plan-then-implement in a file, fresh session for implementation, and "LLMs
  MUST run tests before marking the task done".
- Observed: context-loss thread - after running out of context the agent "forgets the
  architecture" and flipped the sign of a database column in new queries while having
  written the same query correctly minutes before; "subtly inconsistent results that
  would have been very hard to trace"
  (https://news.ycombinator.com/item?id=47516319).

### 5. Context rot: long sessions get measurably dumber
- Observed: same HN thread - "LLMs get dumber as their working memory fills up";
  sessions hitting 200k+ tokens produce incoherent responses; recommended fix is
  splitting plan vs implementation and using subagents for exploration (#47516319).

### 6. The tools themselves ship broken updates
- Observed: claude-code #15692 - "Releases ship faster than bugs get fixed", LSP broken
  across versions, users "reading release notes as a survival mechanism"
  (https://github.com/anthropics/claude-code/issues/15692). Cursor users report a V3
  "significant regression" and buggy/laggy UI
  (https://www.reddit.com/r/cursor/comments/1sc55tc/,
  https://www.reddit.com/r/cursor/comments/1w2ssho/).
- Observed: hangs with no timeout - claude-code #33949 "SSE streaming hangs
  indefinitely (no timeout) + ESC cannot fully cancel"
  (https://github.com/anthropics/claude-code/issues/33949), #26224 "hanging / freezing
  / stuck... 5-20 minutes" (https://github.com/anthropics/claude-code/issues/26224).

### 7. Controls get routed around
- Observed: #84002 - hook-based tool restrictions bypassed in background tasks,
  worktree isolation running destructive git against the main checkout (both confirmed
  and fixed in 2.1.222 per the issue), and the harness dirtying its own worktrees so
  cleanup never collects them. "When I build a control to stop that, it routes around
  the control."

## What this means for the harness (inferred)

| Pain | Our answer today | Gap to build |
|---|---|---|
| False completion (3) | Exit codes decide DONE; events.jsonl is the model-independent record; benchmark pass 3/3 recorded as data | Stall signal: a run that goes quiet must LOOK dead, not fine - war room STALLED badge when events stop (built this pass) |
| Cost opacity (1) | Free-model-only routing, SpendGate daily cap, paid refused by default | Record token usage per call into events so a run's cost is observable data, not a surprise (built this pass) |
| Stops unwatched (2) | Loop has max_iters/time caps and STOPPED_* statuses | Same stall signal; deeper fix (self-wake) is the wake schedule in his environment, not the repo |
| Breaks siblings (4) | Protected-path tamper detection, fresh reviewer, spec gate = plan-then-implement | Benchmark with a seeded multi-file repo where the task touches one file and checks guard the others |
| Context rot (5) | 24k prompt cap, fresh-context reviewer | Nothing new now |
| Broken updates (6) | Everything pinned (DSH, plugins, models), CI on every push | Nothing new now |
| Hangs (6) | 90s client timeout, subprocess timeouts; a hang is a recorded failure | Nothing new now |
| Control bypass (7) | Scope guard, paid-endpoint refusal, key scan, checks can detect tamper of protected files | Nothing new now |
