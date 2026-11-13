"""One-press build (his 2026-11-13 voice note): press enter on "build X" and the harness
detects the ready CLI agents, drafts+reviews a spec, splits it into tasks, distributes them,
and closes each by exit codes. Human approval of the spec stays a hard gate.

`llm`, `approve` and `agents` are injectable so tests run with fakes: no network, no spend.
"""
import json
import re
from pathlib import Path

from . import egm
from .fleet import detect_all, report as fleet_report
from .orchestrate import CLI_TEMPLATES, run_tasks


def ready_agents(fleet_results):
    """{cmd: argv template} for CLIs that probed ready."""
    return {cmd: CLI_TEMPLATES[cmd] for cmd, r in fleet_results.items()
            if r.get("ready") and cmd in CLI_TEMPLATES}


SPLIT_SYS = ("Split this spec into independent coding tasks. Reply with JSON only: "
             "{\"tasks\":[{\"id\":str,\"goal\":str,\"checks\":[shell commands]}]}. "
             "Each task must be doable in its own empty directory.")


def split_tasks(llm, spec_text, fallback_checks):
    """Ask the planner to split the approved spec into tasks; any parse/validation problem
    falls back to one task carrying the spec's own checks. Tasks: [{id, goal, checks}]."""
    raw = llm(SPLIT_SYS, "SPEC:\n" + spec_text)
    tasks = None
    for attempt in range(2):
        if attempt:
            raw = llm(SPLIT_SYS, "Your last reply was not parseable. JSON only.\n\nSPEC:\n" + spec_text)
        m = re.search(r"\{.*\}", raw or "", re.S)
        try:
            tasks = json.loads(m.group(0))["tasks"] if m else None
        except (ValueError, KeyError):
            tasks = None
        if isinstance(tasks, list) and tasks:
            break
    ok = (isinstance(tasks, list) and tasks and all(
        isinstance(t, dict) and t.get("id") and t.get("goal") and
        isinstance(t.get("checks"), list) and all(isinstance(c, str) for c in t["checks"])
        for t in tasks))
    if not ok:
        return [{"id": "t1", "goal": spec_text[:400],
                 "checks": [{"id": f"t1-c{i+1}", "cmd": c["cmd"]} for i, c in enumerate(fallback_checks)]}], "fallback_single_task"
    return [{"id": str(t["id"]), "goal": t["goal"],
             "checks": [{"id": f"{t['id']}-c{i+1}", "cmd": c} for i, c in enumerate(t["checks"])],
             **({"protected": [str(p) for p in t["protected"]]}
                if isinstance(t.get("protected"), list) else {})}
            for t in tasks], "split"


def one_press(goal, base_dir, llm, approve, agents=None, fleet_results=None, max_iters=6):
    """The full flow. agents/fleet_results injectable; real run uses fleet.detect_all()."""
    fleet_results = detect_all() if fleet_results is None and agents is None else (fleet_results or {})
    agents = agents if agents is not None else ready_agents(fleet_results)
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    brief, brief_findings = egm.brainstorm(llm, goal)  # EGM brainstorm: brief before the spec
    Path(base_dir, "concepts_brief.md").write_text(brief)
    spec, findings, checks = egm.spec_gate(llm, goal, base_dir, context=brief)
    if not approve(spec, findings):
        return {"status": "SPEC_NOT_APPROVED", "findings": findings}
    if not checks:
        return {"status": "NO_CHECKS_IN_SPEC", "findings": findings}
    tasks, how = split_tasks(llm, spec, checks)
    if not agents:
        return {"status": "NO_READY_AGENTS", "fleet": fleet_report(fleet_results) if fleet_results else "",
                "tasks": tasks, "split": how}
    results = run_tasks(tasks, agents, base_dir, max_iters=max_iters)
    drift = egm.drift_report(spec, base_dir)  # EGM drift report: spec paths missing after the build
    return {"status": "DONE_VERIFIED" if all(s == "DONE_VERIFIED" for s in results.values()) else "INCOMPLETE",
            "tasks": results, "split": how, "drift": drift, "brief_findings": brief_findings,
            "fleet": fleet_report(fleet_results) if fleet_results else ""}
