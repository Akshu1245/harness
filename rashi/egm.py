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


def invalid_checks(checks, workdir):
    """Findings for checks that name files which do not exist. A check on a missing file can never pass."""
    out = []
    for c in checks:
        for tok in re.findall(r"[\w./-]+\.\w+", c["cmd"]):
            if "/" in tok or tok.endswith((".py", ".sh", ".js")):
                if not (Path(workdir) / tok).exists():
                    out.append({"severity": "high", "issue": f"check {c['id']} references missing file {tok}",
                                "evidence": c["cmd"]})
    return out


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
    """Deterministic: referenced paths missing from the code tree. Same file-token rule as
    invalid_checks: a slash, or a .py/.sh/.js suffix, marks a token as a path (so `3.11` is not one)."""
    def looks_like_path(tok):
        return "/" in tok or tok.endswith((".py", ".sh", ".js"))
    missing = sorted({r for r in dict.fromkeys(PATH_RE.findall(spec_text))
                      if looks_like_path(r) and not (Path(workdir) / r).exists()})
    return {"missing_paths": missing, "drifted": bool(missing)}


def spec_gate(llm, goal, workdir, context="", max_rounds=2):
    """Elephant drafts, goldfish reviews, elephant revises on high findings. Returns (spec, findings, checks).
    Checks must be runnable: they may only name files that exist. If a revision loses or breaks the checks,
    the last valid set is kept. A human still approves the spec before the build loop runs."""
    spec = draft_spec(llm, goal, context)
    findings, valid = [], []
    for _ in range(max_rounds):
        cur = extract_checks(spec)
        bad = invalid_checks(cur, workdir)
        if cur and not bad:
            valid = cur
        findings = goldfish_review(llm, spec, workdir) + bad
        if not any(f.get("severity") == "high" for f in findings):
            break
        spec = llm(ELEPHANT_SYS, "Revise this spec to resolve these findings. Keep the Checks section. "
                   "Checks may only use files that already exist.\nSPEC:\n" + spec + "\nFINDINGS:\n" + json.dumps(findings))
    cur = extract_checks(spec)
    bad = invalid_checks(cur, workdir)
    if cur and not bad:
        valid = cur
    return spec, findings + ([] if not bad else bad), valid
