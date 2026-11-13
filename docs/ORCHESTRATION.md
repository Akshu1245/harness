# Orchestration: one press, many CLI agents

His 2026-11-13 voice note: install the harness on the laptop and it should find which agent CLIs
are installed, test readiness, and say how to fix the rest. Then "build X" runs end to end inside
the harness: research, plan, distribute across the available CLI agents, loop until verifiably
done, and test the features. Ponytail and no-ai-slop rules are consulted before any code is
written (rashi/rules.py, wired into the planner/coder/reviewer prompts).

## What exists now (tested)

- `rashi/fleet.py` - detection + readiness. Probes codex, claude, opencode, aider, droid, gemini
  with `--version` only (read-only, nothing signs in or sends prompts). `fleet.report()` prints
  READY / BROKEN (with the fix) / ABSENT (with the install hint), ready first.
- `rashi/orchestrate.py` - distribution + verified completion.
  - `CliAgent` drives one CLI non-interactively per loop iteration, prompt carries goal + failing
    checks. A non-zero CLI exit is recorded and the loop continues; it never counts as done.
  - `assign` round-robins tasks over ready agents; no ready agent -> `NO_AGENT_AVAILABLE`.
  - `run_tasks` gives each task its OWN subdirectory (two agents never edit the same tree) and
    closes it with `loop.run_loop`: DONE_VERIFIED only when the task's checks exit 0.
- `rashi/build.py` - the one-press entry: detect fleet -> spec gate (human approval stays a hard
  gate) -> planner splits the spec into independent tasks (unparsable split falls back to one
  task) -> distribute -> DONE_VERIFIED only when every task verifies.
- `rashi/rules.py` - the standing ponytail (smallest complete change) and no-ai-slop rules,
  distilled from the two repos he sent (both MIT), wired into `rashi/roles.py`.

## What is deliberately not built

- **Multi-account Codex rotation** (four Codex accounts live at once, switching when limits hit).
  Flagged to him for a decision first: pooling accounts to multiply rate limits is the kind of
  usage OpenAI's rules prohibit, and the risk is suspension of all four accounts. The orchestrator
  already runs N configured CLI sessions; the account-switching piece (isolated CODEX_HOME
  profiles, like the 0-star olliecrow/multicodex or 11ArkaN/codex-switcher) stays unbuilt until
  he accepts that risk explicitly.
- **Live CLI invocation flags.** `CLI_TEMPLATES` are best-effort and UNVERIFIED until run against
  the real CLIs on his laptop; fleet probes tell us which CLIs are present before anything runs.

## Open-source references (verified live 2026-11-13)

- BloopAI/vibe-kanban (28,673 stars, Apache-2.0): the leading multi-agent orchestrator UI
  (kanban over Claude Code, Codex, Gemini). Reference for the front door; too large to embed.
- brizzai/fleet (61 stars, Apache-2.0): tmux TUI for parallel Claude Code sessions. Reference.
- yohey-w/multi-agent-shogun (1,421 stars, MIT): tmux multi-agent for Claude Code. Reference.
- Deep dive detail in docs/REUSE.md.
