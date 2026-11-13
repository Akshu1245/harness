# Gaps found and fixed

Running list (his instruction 2026-11-13 10:52pm): gaps the old plan or earlier prompts skipped,
found by audits / mutation testing / live runs / fresh-env runs, each with proof. Newest first.

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
