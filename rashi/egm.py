"""Elephant/Goldfish pattern (idea from google/elephant-goldfish-model, Apache-2.0; clean-room code).

Elephant: holds project context, drafts a spec. Goldfish: a fresh call that sees ONLY the spec
and the files it references, never the elephant's conversation. Findings are structured JSON.
Drift report is deterministic: every file/symbol a spec references must exist in the code.
`llm` is any callable llm(system, user) -> str, so tests run with no network and no spend.
Reviews are advisory; check exit codes still decide DONE.
"""
import json, re
from pathlib import Path

from .rules import NEVER_LIE

ELEPHANT_SYS = ("You draft a software spec. Output markdown with sections: Goal, Constraints, "
                "Files (one `path` per bullet), Checks (one shell command per bullet in backticks), "
                "Out of scope. Be concrete and testable. " + NEVER_LIE)
GOLDFISH_SYS = ("You are a fresh reviewer with no prior context. Review ONLY the spec and files given. "
                "Reply with JSON only: {\"findings\":[{\"severity\":\"high|med|low\",\"issue\":str,"
                "\"evidence\":str}]}. Flag unstated assumptions, untestable requirements, missing checks.")
BRIEF_SYS = ("You hold the project context. Turn the idea into a concept brief. Output markdown with "
             "sections: Problem, Proposed direction, Trade-offs, Open questions. Be concrete. " + NEVER_LIE)
CHALLENGE_SYS = ("You are a fresh reviewer with no prior context. Challenge ONLY the concept brief given. "
                 "Reply with JSON only: {\"findings\":[{\"severity\":\"high|med|low\",\"issue\":str,"
                 "\"evidence\":str}]}. Flag unstated assumptions, fuzzy goals, missing constraints.")
PATH_RE = re.compile(r"`([\w./-]+\.\w+)`")
CHECK_RE = re.compile(r"^\s*[-*]\s*`([^`]+)`\s*$", re.M)


def draft_spec(llm, goal, context=""):
    spec = llm(ELEPHANT_SYS, f"Project context:\n{context[:6000]}\n\nGoal: {goal}")
    if not spec.strip():  # free-tier models sometimes return an empty message; ask once more
        spec = llm(ELEPHANT_SYS, f"Project context:\n{context[:6000]}\n\nGoal: {goal}\n\n"
                                 "Your previous reply was empty. Write the spec now.")
    return spec


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


# Commands that execute a file directly: the file must exist beforehand or the check can never
# pass. Creation assertions like `test -f app.py` are fine on missing files - absence is the point.
_RUNNERS = ("python", "python3", "pytest", "sh", "bash", "node", "ruby", "pip")
_OPS = {"|", "||", "&&", ";", "|&"}


def invalid_checks(checks, workdir):
    """Findings for checks that execute files which do not exist. A file token is 'executed' when
    it follows a runner (python/pytest/sh/...) anywhere before a shell operator, or sits in command
    position itself (./run.sh). Creation assertions like `test -f app.py` name no runner, so a
    missing file is fine there - absence is what the check asserts."""
    out = []
    for c in checks:
        toks = c["cmd"].split()
        runner_seen = False
        for i, tok in enumerate(toks):
            if tok in _OPS:
                runner_seen = False
                continue
            if tok in _RUNNERS or tok.rsplit("/", 1)[-1] in _RUNNERS:
                runner_seen = True
                continue
            if not (runner_seen or i == 0 or toks[i - 1] in _OPS):
                continue
            for m in re.findall(r"[\w./-]+\.\w+", tok):
                if ("/" in m or m.endswith((".py", ".sh", ".js"))) and not (Path(workdir) / m).exists():
                    out.append({"severity": "high", "issue": f"check {c['id']} executes missing file {m}",
                                "evidence": c["cmd"]})
    return out


def _findings_from(llm, system, user):
    """Two-attempt JSON findings call: free-tier models sometimes answer prose; one reminder
    fixes the shape (live run 2026-11-13). Unparsable twice = one high finding, never a crash."""
    for attempt in range(2):
        raw = llm(system, user if attempt == 0 else
                  "Your last reply was not parseable. Reply with JSON only, nothing else.\n\n" + user)
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            findings = json.loads(m.group(0))["findings"] if m else None
        except (ValueError, KeyError):
            findings = None
        if isinstance(findings, list):
            return [f for f in findings if isinstance(f, dict) and "issue" in f]
    return [{"severity": "high", "issue": "reviewer output unparsable", "evidence": raw[:200]}]


def brainstorm(llm, goal, context=""):
    """EGM brainstorm: elephant turns the idea into a concept brief with full project context,
    a fresh goldfish challenges it, elephant revises once on high findings. The caller saves the
    brief as concepts_brief.md (EGM's layout). Returns (brief, challenge_findings)."""
    ask = f"Project context:\n{context[:6000]}\n\nIdea: {goal}"
    brief = llm(BRIEF_SYS, ask)
    if not brief.strip():  # same empty-reply failure mode as draft_spec
        brief = llm(BRIEF_SYS, ask + "\n\nYour previous reply was empty. Write the brief now.")
    findings = _findings_from(llm, CHALLENGE_SYS, "BRIEF:\n" + brief)
    if any(f.get("severity") == "high" for f in findings):
        brief = llm(BRIEF_SYS, "Revise this brief to resolve these findings. Keep the sections.\n"
                    "BRIEF:\n" + brief + "\nFINDINGS:\n" + json.dumps(findings))
    return brief, findings


def goldfish_review(llm, spec_text, workdir):
    """Fresh context: only the spec and referenced files are passed. One JSON-strictness retry:
    the live flash-model run (2026-11-13) answered with prose once; a reminder fixed the shape."""
    refs = "".join(f"\n--- {r} ---\n{t}" for r, t in referenced_files(spec_text, workdir))
    user = f"SPEC:\n{spec_text}\n\nREFERENCED FILES:{refs or ' (none)'}"
    return _findings_from(llm, GOLDFISH_SYS, user)


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
