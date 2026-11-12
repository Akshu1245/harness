"""Elephant/Goldfish pattern (idea from google/elephant-goldfish-model, Apache-2.0; clean-room code).

Elephant: holds project context, drafts a spec. Goldfish: a fresh call that sees ONLY the spec
and the files it references, never the elephant's conversation. Findings are structured JSON.
Drift report is deterministic: every file/symbol a spec references must exist in the code.
`llm` is any callable llm(system, user) -> str, so tests run with no network and no spend.
Reviews are advisory; check exit codes still decide DONE.
"""
import json, re
from pathlib import Path

ELEPHANT_SYS = ("You draft a software spec. Output markdown with sections: Goal, Constraints, "
                "Files (one `path` per bullet), Checks (one shell command per bullet in backticks), "
                "Out of scope. Be concrete and testable.")
GOLDFISH_SYS = ("You are a fresh reviewer with no prior context. Review ONLY the spec and files given. "
                "Reply with JSON only: {\"findings\":[{\"severity\":\"high|med|low\",\"issue\":str,"
                "\"evidence\":str}]}. Flag unstated assumptions, untestable requirements, missing checks.")
PATH_RE = re.compile(r"`([\w./-]+\.\w+)`")
CHECK_RE = re.compile(r"^\s*[-*]\s*`([^`]+)`\s*$", re.M)


def draft_spec(llm, goal, context=""):
    return llm(ELEPHANT_SYS, f"Project context:\n{context[:6000]}\n\nGoal: {goal}")


def referenced_files(spec_text, workdir):
    out = []
    for rel in dict.fromkeys(PATH_RE.findall(spec_text)):
        p = (Path(workdir) / rel).resolve()
        if Path(workdir).resolve() in p.parents and p.is_file():
            out.append((rel, p.read_text(errors="replace")[:4000]))
    return out


def extract_checks(spec_text):
    cmds = [c for c in CHECK_RE.findall(spec_text) if not PATH_RE.fullmatch(f"`{c}`")]
    return [{"id": f"c{i+1}", "cmd": c} for i, c in enumerate(cmds)]


def goldfish_review(llm, spec_text, workdir):
    """Fresh context: only the spec and referenced files are passed."""
    refs = "".join(f"\n--- {r} ---\n{t}" for r, t in referenced_files(spec_text, workdir))
    raw = llm(GOLDFISH_SYS, f"SPEC:\n{spec_text}\n\nREFERENCED FILES:{refs or ' (none)'}")
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        findings = json.loads(m.group(0))["findings"] if m else None
    except (ValueError, KeyError):
        findings = None
    if not isinstance(findings, list):
        return [{"severity": "high", "issue": "reviewer output unparsable", "evidence": raw[:200]}]
    return [f for f in findings if isinstance(f, dict) and "issue" in f]


def drift_report(spec_text, workdir):
    """Deterministic: referenced paths missing from the code tree."""
    missing = [r for r in dict.fromkeys(PATH_RE.findall(spec_text))
               if not (Path(workdir) / r).exists() and "/" in r or r.endswith(".py") and not (Path(workdir) / r).exists()]
    return {"missing_paths": sorted(set(missing)), "drifted": bool(missing)}


def spec_gate(llm, goal, workdir, context="", max_rounds=2):
    """Elephant drafts, goldfish reviews, elephant revises on high findings. Returns (spec, findings, checks).
    A human still approves the spec before the build loop runs."""
    spec = draft_spec(llm, goal, context)
    findings = []
    for _ in range(max_rounds):
        findings = goldfish_review(llm, spec, workdir)
        if not any(f.get("severity") == "high" for f in findings):
            break
        spec = llm(ELEPHANT_SYS, f"Revise this spec to resolve these findings.\nSPEC:\n{spec}\nFINDINGS:\n{json.dumps(findings)}")
    return spec, findings, extract_checks(spec)
