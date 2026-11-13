# Current verification corrections

The product is partially built. Older entries below record implementation milestones, not full product acceptance.

- DSH: plugin composition is verified, not full model-to-tool execution. Build is now disabled in DSH and MCP until a generated-spec review/approval handshake exists. No unconditional approval.
- Council: fake-member tests pass; a real 16-model debate has not run. Model overrides now reject non-free identifiers before client creation. A free identifier alone is not a guarantee of future provider pricing.
- Sandbox: if requested but bwrap is missing, stop before agents or checks. No unsandboxed fallback. Only check commands use this profile; CLI agents are NOT confined by it. The read-only system mount does not hide private readable files.
- Tracing: measured the real loop, not an empty block. Root spans close on errors/early returns. Local JSONL only, no Langfuse export.
- Research: GitHub API candidates are discovery only, not vetted recommendations. Error-shaped API responses now report failure instead of "nothing found".
- MCP: malformed JSON values now return invalid-request errors without crashing.
- Rollback/resume remain partial: deletion recovery, bounded memory, symlink containment, persistent spec identity and full resume feedback need further hardening before safety claims.

Tests: regressions cover fail-closed sandbox, paid override rejection, no auto-approval through MCP/DSH, real loop event containment and exception spans, malformed MCP requests and search API errors.

# Gaps found and fixed

Running list (his instruction 2026-11-13 10:52pm): gaps the old plan or earlier prompts skipped,
found by audits / mutation testing / live runs / fresh-env runs, each with proof. Newest first.

## 2026-11-13 11pm - B11 MCP
1. **B11 MCP missing.** Agent CLIs could not call the harness as a tool server. Fixed:
   rashi/mcp_server.py - MCP stdio JSON-RPC (protocol 2024-11-05) in pure stdlib, exposing
   rashi_fleet / rashi_research / rashi_drift / rashi_ask / rashi_build. Tool failures are tool
   errors (isError), never server crashes; keyless tools work without any provider key, ask/build
   say honestly when no key is set. Verified with a live stdio session (initialize + a real
   rashi_research call returning GitHub results). Proof: tests/test_mcp_server.py (4).

## 2026-11-13 11pm - R28 research department
1. **R28 research-before-building missing from the product.** REUSE.md was process only. Fixed:
   rashi/research.py - most-starred GitHub repos for a topic via the keyless search API, with
   stars and descriptions, honest on failure (no invented hits). `rashi research "topic"` CLI and
   `rashi build --research` feed findings into the EGM brief. Note: DuckDuckGo HTML was tried
   first and silently returns an anomaly page from datacenter IPs (observed live) - GitHub search
   is the working keyless source and answers his "good number of stars" rule directly. Proof:
   tests/test_research.py (4), test_one_press_research_feeds_the_brief, live CLI run verified.

## 2026-11-13 11pm - R29 memory
1. **R29 second brain missing.** Nothing carried learnings between runs. Fixed:
   rashi/memory.py (append-only .rashi/memory.jsonl; the loop records done/rollback/stall;
   recall feeds the next brainstorm + spec gate in both build paths; capped, corrupt lines
   skipped, no LLM summarizing so zero spend). Proof: tests/test_memory.py (4).

## 2026-11-13 11pm - B1 sandboxed checks
1. **B1 checks ran unsandboxed.** Any check command had full user fs/network. Fixed:
   rashi/sandbox.py (bwrap profile per the DSH sandbox-local pattern, reimplemented) wired into
   every check run incl. the new baseline; off by default, spec["sandbox"]/RASHI_SANDBOX=1 enables;
   missing bwrap warns in the event log, never silent. Verified with REAL bwrap 0.6.1: workdir
   writable, /etc write blocked, network unreachable. Proof:
   tests/test_hardening.py::test_sandboxed_check_cannot_touch_outside_workdir (live bwrap),
   test_sandbox_requested_without_bwrap_warns_not_silent.

## 2026-11-13 11pm - R9 council
1. **R9 multi-model debate + vote missing from the package.** The old root scripts
   (run_rashi_council.py, run_architecture_council.py) polled gateways once and dumped JSON -
   not reusable, not testable, dotenv-dependent. Fixed: rashi/council.py (independent answers,
   anonymized peer vote, no self-votes, deterministic tally, sick members excluded and recorded,
   advisory only) + `rashi council "question"` CLI with per-gateway free-model members
   (non-Kenari defaults marked UNVERIFIED until a live run). Proof: tests/test_council.py (5),
   tests/test_main.py (2).

## 2026-11-13 11pm (archive gap list B-items)
1. **B6 resume missing.** An interrupted run restarted from zero. Fixed: run_loop resumes from
   PROGRESS.json when goal matches and status is unfinished; emits `resumed`. Proof:
   tests/test_loop.py::test_resume_continues_an_interrupted_run (+ ignores done/other-goal runs).
2. **B5 per-step rollback missing.** A regressing agent step stayed in the tree. Fixed: baseline
   check run before the loop, per-step content stash (.rashi/rollback/), set-difference regression
   rule, undo + agent told not to re-apply. Tampering check at baseline fails closed with evidence
   (found by test_check_tampering_protected_file_fails during the change). Proof:
   test_regression_rolls_back_the_bad_step, test_rollback_deletes_added_files.
3. **B3 repo map missing.** The elephant drafted specs blind to the actual tree. Fixed:
   rashi/repomap.py (deterministic, stdlib, capped, says when truncated) wired as context into
   brainstorm + spec gate in both build paths. Proof: tests/test_repomap.py (4 tests).

## 2026-11-13 late evening
1. **EGM drift report never ran.** `drift_report` existed but no pipeline called it - found by
   re-reading google/elephant-goldfish-model (drift report is one of its core skills). Fixed:
   pipeline + one_press now emit drift after every build; `rashi drift SPEC DIR` CLI (exit 1 on
   drift). Proof: tests/test_pipeline.py::test_pipeline_emits_drift_event,
   tests/test_build.py::test_one_press_drift_flags_spec_paths_never_built.
2. **EGM brainstorm missing.** The brief-before-spec step (concepts_brief.md, fresh-reviewer
   challenge) did not exist. Fixed: egm.brainstorm wired into one_press, brief saved as
   concepts_brief.md and fed to the spec gate. Proof: tests/test_egm.py::test_brainstorm_*.
3. **DSH plugin could not load from outside the DSH checkout.** Boot test (pnpm dsh web --patch)
   failed: `@deepseek-ai/dsh-tools` only resolves inside the monorepo. Fixed: dsh/README.md setup
   now says copy the plugin into the checkout; load verified via headless boot reaching the LLM
   credential stage with the rashi plugin composed (startup log `include:rashi`).

## 2026-11-13 evening (from mutation testing + soak + fresh-clone runs)
4. **4 weak benchmark checks passed hardcoded solutions** - found by writing mutants against the
   checks. Fixed: checks now assert multiple inputs/values. Proof: tests/test_bench.py mutants.
5. **split_tasks dropped model-declared protected paths** - soak scenario caught it. Fixed
   (0121e65).
6. **Import-time OpenAI client crash on keyless machines** - fresh-clone run caught it. Fixed:
   client constructed lazily inside make_llm.
7. **Benchmark check depending on pytest failed on bare python** - checks must assume stdlib
   only. Fixed in tasks.json.
8. **Empty spec draft from flash model flowed downstream** - live Kenari run. Fixed: draft_spec
   asks once more on an empty reply (test_draft_spec_retries_an_empty_reply).
9. **Fallback check-shape crash** - live end-to-end run. Fixed before push (see git log).

## Public benchmark work, 2026-11-13 11:12pm

- Gap: local toy tasks alone were not public benchmark evidence. Added `rashi public-bench`, a stdlib HumanEval subset adapter with separated prompt-only generation, fixed one-attempt denominator, data hash and saved completions. Full vetted list and future external evaluators: [PUBLIC_BENCHMARKS.md](PUBLIC_BENCHMARKS.md).
- Verification: upstream HumanEval/0..2 canonical calibration 3/3, deliberately broken completions 0/3. These are evaluator self-tests, not a model score. Model measurement awaits free quota.
- The public grader uses a new bwrap root rather than read-only host root. Tests check private paths/env are not exposed and early exit is not a pass. This is defense in depth, not a claim of a fully adversarial sandbox.
- Deferred with reasons: heavyweight Docker suites, unresolved exercise/dataset redistribution rights, and full-set statistical/contamination analysis. Nothing has been silently called fully ready.
