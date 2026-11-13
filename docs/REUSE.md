# Reuse before rebuild (stars and licence checked live 2026-11-12 via search results)
| Component | Candidate | Stars | Licence | Decision |
|---|---|---|---|---|
| Coding-agent core | SWE-agent/mini-swe-agent | 9,567 | MIT | candidate for coder runtime; not yet integrated |
| Agent framework | langchain-ai/deepagents | 31,233 | MIT | candidate; heavy dependency, not yet integrated |
| Full agent platform | OpenHands/OpenHands | 93,306 | MIT | reference; too large to embed |
| Terminal pair-coder | Aider-AI/aider | 50,072 | Apache-2.0 | reference |
| LLM routing | lm-sys/RouteLLM | 5,697 | Apache-2.0 | candidate for the cost router baseline |
| Provider proxy/budgets | BerriAI/litellm | n/a here | check repo (mixed: enterprise dir is separate) | verify licence before use |
| Evals | promptfoo/promptfoo | 27,076 | MIT | candidate for calibration and regression evals |
| Bounty scope parsing | root4loot/rescope | 331 | MIT | candidate for importing program scopes |
| Spec + fresh reviewers | google/elephant-goldfish-model | 17,820 | Apache-2.0 | pattern reimplemented in rashi/egm.py |
| Decision router | NandhaKishorM/laya | n/a | Apache-2.0 | first-preference router, measured |
| Approval/permission modes | deepseek-ai/deepseek-harness permission presets (`/permission`, ui-permission-presets): readOnly / workspaceWrite / fullAccess over the sandbox-mode + approval-policy knobs, full-access behind an explicit confirm | (same row) | HIS three modes (full access / review-and-accept / ask-for-everything) live here - do NOT rebuild them in rashi (his 2026-11-13 10:31pm message) |
| IDE front door | deepseek-ai/deepseek-harness | 280,228 | MIT | pinned at 39163dd30f703a79079e2d2446545cff3c453738 (master, 2026-11-13) = npm @deepseek-ai/dsh@0.2.2-rc.3; installed and boot-verified 2026-11-13, see docs/DSH_SETUP.md |
| Android app | saya-ch/dsh-mobile | 846 | Apache-2.0 | pinned at 1616b43b61c7b22c170da1dc1eccdc4053c0cfbd (main, 2026-11-13) = npm dsh-mobile@0.8.8; installed into the dsh web profile 2026-11-13, phone pairing runs on his laptop |
| Minimal-diff coding rules | DietrichGebert/ponytail | 190,051 | MIT | rules distilled into rashi/rules.py (AGENTS.md, main, 2026-11-13); always consulted |
| Anti-slop writing rules | petergyang/no-ai-slop | 13,452 | MIT | rules distilled into rashi/rules.py (SKILL.md, main, 2026-11-13); always consulted |
| Multi-agent orchestrator UI | BloopAI/vibe-kanban | 28,673 | Apache-2.0 | reference for the front door; too large to embed |
| Parallel CLI sessions (tmux) | brizzai/fleet | 61 | Apache-2.0 | reference; our fleet.py/orchestrate.py is the minimal in-repo version |
| Multi-agent tmux system | yohey-w/multi-agent-shogun | 1,421 | MIT | reference |
| Codex account switching | olliecrow/multicodex, 11ArkaN/codex-switcher | 0 / 0 | Apache-2.0 / ISC | UNVETTED, 0 stars; account rotation held for his decision (ToS risk flagged 2026-11-13) |
Excluded: OpenJev (CC BY-NC, not commercial-safe).
