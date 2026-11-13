"""One-press orchestration (his 2026-11-13 voice note): from the harness alone, "build X" is
researched, planned, split into tasks, and distributed across the available CLI agents, each task
closed by the verified loop - exit codes decide DONE, never a model's claim.

Pieces here:
- CliAgent: adapter that drives one installed CLI coding agent non-interactively.
- assign: round-robin tasks over the agents that fleet.detect_all found ready.
- run_tasks: each task runs in its OWN subdirectory (parallel agents never share a workdir),
  through loop.run_loop, so every task ends DONE_VERIFIED / STOPPED_* / FAILED_* by exit codes.

CLI invocation templates are best-effort and marked unverified until run against the real CLIs
on his laptop; fleet.report tells him which agents are ready before anything is assigned.
"""
import subprocess
from pathlib import Path

from .loop import changed_since, run_loop, snapshot

# Non-interactive invocation per CLI. UNVERIFIED until probed live; fix from each CLI's docs.
CLI_TEMPLATES = {
    "codex": ["codex", "exec", "--full-auto", "{prompt}"],
    "claude": ["claude", "-p", "{prompt}", "--dangerously-skip-permissions"],
    "opencode": ["opencode", "run", "{prompt}"],
    "aider": ["aider", "--yes", "--message", "{prompt}"],
    "droid": ["droid", "exec", "{prompt}"],
    "gemini": ["gemini", "--yolo", "{prompt}"],
}


class CliAgent:
    """loop.run_loop agent callable: one CLI invocation per iteration, prompt carries goal+feedback."""

    def __init__(self, argv, timeout=600):
        self.argv, self.timeout = argv, timeout

    @classmethod
    def for_cli(cls, cmd, timeout=600):
        if cmd not in CLI_TEMPLATES:
            raise ValueError(f"no invocation template for {cmd}")
        return cls(CLI_TEMPLATES[cmd], timeout)

    def __call__(self, goal, feedback, workdir):
        prompt = f"Goal: {goal}\nWork only inside the current directory."
        if feedback:
            prompt += f"\nFailing checks to fix:\n{feedback}"
        argv = [a.replace("{prompt}", prompt) for a in self.argv]
        p = subprocess.run(argv, cwd=workdir, capture_output=True, text=True, timeout=self.timeout)
        if p.returncode != 0:
            raise RuntimeError(f"{self.argv[0]} exited {p.returncode}: {(p.stderr or p.stdout)[-300:]}")


def assign(tasks, agents):
    """Round-robin task -> agent name. Deterministic; an empty agent list assigns nothing."""
    out = {}
    names = sorted(agents)
    for i, t in enumerate(tasks):
        if names:
            out[t["id"]] = names[i % len(names)]
    return out


def run_tasks(tasks, agents, base_dir, max_iters=6, timeout=600):
    """tasks: [{id, goal, checks, protected?}]. agents: {name: argv list, CliAgent, or any
    loop-compatible callable agent(goal, feedback, workdir) - e.g. llm_agent.make_agent(...)}.
    Each task runs in its own workdir. After each task, the files it changed are passed
    to later tasks as sibling context - ACM EXPRESS'26 measured that a message describing
    the completed concurrent change recovers 82% of pass-alone/fail-together runs."""
    base = Path(base_dir)
    results = {}
    plan = assign(tasks, agents)
    sibling_changes = {}
    for t in tasks:
        name = plan.get(t["id"])
        if name is None:
            results[t["id"]] = "NO_AGENT_AVAILABLE"
            continue
        agent = agents[name]
        if not isinstance(agent, CliAgent) and not callable(agent):
            agent = CliAgent(agent, timeout=timeout)
        wd = base / t["id"]
        wd.mkdir(parents=True, exist_ok=True)
        goal = t["goal"]
        if sibling_changes:
            ctx = "\n".join(f"- {tid}: {', '.join(files)}" for tid, files in sibling_changes.items())
            goal += ("\n\nSibling tasks in this build already changed these files; if your work "
                     "interacts with them, match their interfaces instead of reinventing them:\n" + ctx)
        before = snapshot(wd)
        spec = {"goal": goal, "workdir": str(wd), "protected": t.get("protected", []),
                "checks": t["checks"], "max_iters": max_iters}
        status, _ = run_loop(spec, agent)
        results[t["id"]] = status
        changed = changed_since(before, wd)["changed"]
        changed = [c for c in changed if c not in ("PROGRESS.json", "events.jsonl", ".replay.jsonl")
                   and not c.startswith(".spill/")]
        if changed:
            sibling_changes[t["id"]] = changed
    return results
