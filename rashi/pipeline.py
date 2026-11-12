"""End to end: spec (elephant+goldfish) -> human approval -> verified loop -> fresh review of the result.
approve(spec, findings) -> bool is the human gate. Review findings never change the DONE status."""
from . import egm
from .loop import run_loop
from .router import route


def run_pipeline(goal, workdir, llm, agent, approve, protected=(), laya=None, log_path=None, max_iters=6):
    role, rec = route(goal, laya=laya, log_path=log_path)
    spec, findings, checks = egm.spec_gate(llm, goal, workdir)
    if not approve(spec, findings):
        return {"status": "SPEC_NOT_APPROVED", "role": role, "findings": findings}
    if not checks:
        return {"status": "NO_CHECKS_IN_SPEC", "role": role, "findings": findings}
    status, log = run_loop({"goal": goal, "checks": checks, "protected": list(protected),
                            "workdir": workdir, "max_iters": max_iters}, agent)
    review = egm.goldfish_review(llm, spec, workdir) if status == "DONE_VERIFIED" else []
    return {"status": status, "role": role, "spec_findings": findings, "review": review, "iters": len(log)}
