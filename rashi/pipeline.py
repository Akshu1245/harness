"""End to end: spec (elephant+goldfish) -> human approval -> verified loop -> fresh review of the result.
approve(spec, findings) -> bool is the human gate. Review findings never change the DONE status."""
import re
from pathlib import Path
from . import egm
from .loop import changed_since, emit, run_loop, snapshot
from .router import route


def run_pipeline(goal, workdir, llm, agent, approve, protected=(), laya=None, log_path=None, max_iters=6):
    Path(workdir).mkdir(parents=True, exist_ok=True)
    role, rec = route(goal, laya=laya, log_path=log_path)
    emit(workdir, "route", role=role, decider=rec["decider"], rules_role=rec["rules_role"])
    spec, findings, checks = egm.spec_gate(llm, goal, workdir)
    if not approve(spec, findings):
        return {"status": "SPEC_NOT_APPROVED", "role": role, "findings": findings}
    if not checks:
        return {"status": "NO_CHECKS_IN_SPEC", "role": role, "findings": findings}
    before = snapshot(workdir)
    status, log = run_loop({"goal": goal, "checks": checks, "protected": list(protected),
                            "workdir": workdir, "max_iters": max_iters}, agent)
    # Deterministic scope check: files the agent touched that the spec never named. Advisory,
    # like review findings; exit codes still decide DONE. PROGRESS.json is the loop's own state.
    # shortcut: declared scope = every backticked path plus every file token in check commands,
    # upgrade: parse only the Files section when specs get large enough to make this noisy.
    declared = set(egm.PATH_RE.findall(spec)) | {"PROGRESS.json", ".spend.json", "events.jsonl"}
    for c in checks:
        declared.update(re.findall(r"[\w./-]+\.\w+", c["cmd"]))
    touched = changed_since(before, workdir)
    scope = {"out_of_scope": sorted(p for p in touched["changed"] + touched["removed"] if p not in declared),
             "touched": len(touched["changed"]), "removed": touched["removed"]}
    if scope["out_of_scope"]:
        emit(workdir, "scope", out_of_scope=scope["out_of_scope"])
    review = egm.goldfish_review(llm, spec, workdir) if status == "DONE_VERIFIED" else []
    drift = egm.drift_report(spec, workdir)  # EGM drift report: what the spec named that build missed
    if drift["drifted"]:
        emit(workdir, "drift", missing=drift["missing_paths"])
    return {"status": status, "role": role, "spec_findings": findings, "review": review,
            "scope": scope, "drift": drift, "iters": len(log)}
