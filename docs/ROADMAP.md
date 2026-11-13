# Roadmap: what makes this a real harness (owner: Instinct, 2026-11-13)

Ranked by what each item proves. "Needs him" marks the only items blocked on a
decision or his hardware. Everything else is in motion under the existing grants
(zero spend, push to this repo pre-approved, honest claims only).

## Done and verified (foundation)

- Core build loop with real exit-code checks; DONE only when checks pass (76+ live and unit verified).
- Spec gate: a human approves the spec before code is written.
- Hardened trust boundaries: SSRF guard (incl. IPv6 + CGNAT ranges), scope guard, atomic spend cap, key scan, paid probes refused by default.
- One-press build over a fleet of detected agent CLIs; ponytail/no-ai-slop rules locked into prompts and tests.
- War room serves the real events.jsonl stream; README/docs claim only what exists.
- DSH front door + Simular box installed and verified (docs/DSH_SETUP.md).

## Ranked next

1. **CI on every push (GitHub Actions, free on public repos).** Proves the 81-test
   gate runs in public on every commit; the repo badge makes "verifiable" visible.
   Status: done 2026-11-13 (.github/workflows/tests.yml).
2. **A repeated-run benchmark: 3 fixed build tasks run live on free models, results
   appended to docs/MODELS.md.** Proves reliability with numbers (pass rate,
   iterations, failures), not one demo. Zero spend (Kenari free tier).
3. **Run the test suite on the Simular box over MCP.** Proves the box works as a
   clean second machine and gives a fresh-environment install test.
4. **README quickstart that a stranger can run in 5 minutes.** Proves shippability;
   claims stay limited to what CI and MODELS.md show.
5. **Dogfood: use one_press on a small real feature in this repo.** Proves the loop
   on its own codebase; any crash found is fixed at the root (already happened once:
   the split-fallback bug).
6. **CLI fleet verification on real CLIs.** Needs him: his laptop with codex/claude/
   opencode installed. Until then CLI_TEMPLATES stay marked unverified.
7. **Real Laya router run.** Needs him: hardware for model weights; the adapter is
   honest about being unverified until then.
8. **Multi-Codex account rotation.** Needs him: ToS risk flagged 2026-11-13; not
   built without his explicit decision.
9. **DSH as the daily driver front door + phone pairing.** Needs him: run
   scripts/install_dsh.sh on his laptop, then dsh-mobile setup for LAN pairing.

## Explicitly not doing

- No paid endpoints, no card, no prod deploys, no boxes.dev.
- No account rotation or multi-account tricks without his decision.
- No invented traction, benchmark numbers, or capabilities in any doc.
