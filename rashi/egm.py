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

ELEPHANT_SYS = ('Draft a compact software spec as ONE JSON object, no markdown fences. '
                'Schema: {"goal":str,"constraints":[str],"files":[str],"checks":[str],'
                '"out_of_scope":[str]}. Every key is required. Use 1-3 single-line POSIX shell '
                'checks with semantic assertions, Python stdlib only where possible. Keep JSON '
                'under 1800 characters. Do not repeat long examples or include explanations. '
                'Checks run AFTER implementation; no missing external test scripts. ' + NEVER_LIE)
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


class IncompleteModelOutput(ValueError):
    """Provider explicitly reports a truncated response."""


def _complete_spec(raw):
    """Validate whole structured response; tolerate complete legacy markdown, never partial JSON."""
    import shlex
    if not isinstance(raw,str) or not raw.strip():
        return None
    text=raw.strip()
    if text.startswith('```') and text.endswith('```'):
        text='\n'.join(text.splitlines()[1:-1]).strip()
    if text.startswith('{'):
        try:obj=json.loads(text)
        except ValueError:return None
        if not isinstance(obj,dict) or not isinstance(obj.get('goal'),str) or not obj['goal'].strip():return None
        for key in ('constraints','files','checks','out_of_scope'):
            if not isinstance(obj.get(key),list) or any(not isinstance(v,str) for v in obj[key]):return None
        if not obj['files'] or not obj['checks'] or len(obj['checks'])>12:return None
        # Commands containing backticks cannot be represented losslessly in our legacy markdown.
        if any(not c.strip() or '\n' in c or '`' in c for c in obj['checks']):return None
        text='\n\n'.join(['# Goal\n'+obj['goal']] + [
            '## '+title+'\n'+'\n'.join('- '+('`'+v+'`' if key in ('files','checks') else v)
                                          for v in obj[key])
            for key,title in [('constraints','Constraints'),('files','Files'),('checks','Checks'),('out_of_scope','Out of scope')]])
    if text.count('```') % 2 or text.count('`') % 2:return None
    checks=extract_checks(text)
    if not checks:return None
    for check in checks:
        try:shlex.split(check['cmd'])
        except ValueError:return None
    return text


def _request_spec(llm,prompt):
    """Two attempts, preserving failure instead of passing empty/truncated text onward."""
    raw=''
    for attempt in range(2):
        try:
            raw=llm(ELEPHANT_SYS,prompt if not attempt else prompt+
                    '\nYour previous reply was empty or incomplete. Return the complete compact JSON object now.')
        except IncompleteModelOutput:
            continue
        complete=_complete_spec(raw)
        if complete is not None:return complete
    return None


def draft_spec(llm, goal, context=""):
    return _request_spec(llm,f"Project context:\n{context[:6000]}\n\nGoal: {goal}") or ''


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


def invalid_checks(checks, workdir, expected_files=()):
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
                if ("/" in m or m.endswith((".py", ".sh", ".js"))) and not (Path(workdir) / m).exists() and m not in expected_files:
                    out.append({"severity": "high", "issue": f"check {c['id']} executes missing file {m}",
                                "evidence": c["cmd"]})
    return out


def _findings_from(llm, system, user):
    """Two-attempt JSON findings call: free-tier models sometimes answer prose; one reminder
    fixes the shape (live run 2026-11-13). Unparsable twice = one high finding, never a crash."""
    for attempt in range(2):
        try:
            raw = llm(system, user if attempt == 0 else
                      "Your last reply was empty, incomplete or not parseable. Reply with compact JSON only, nothing else.\n\n" + user)
        except IncompleteModelOutput:
            raw = "provider reported truncated reviewer output"
            continue
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


def declared_outputs(spec):
    """Only explicitly listed relative output files, not incidental command/path mentions."""
    match=re.search(r'(?mi)^#{0,6}\s*Files\s*\n(.*?)(?=^#{1,6}\s|\Z)',spec,re.S|re.M)
    if not match:return set()
    return {p for p in PATH_RE.findall(match.group(1))
            if not Path(p).is_absolute() and '..' not in Path(p).parts}


def spec_gate(llm, goal, workdir, context="", max_rounds=2):
    """Bounded draft/review/revision. Checks always belong to the returned exact spec.
    An incomplete revision retains the last complete spec and adds a high finding.
    This is advisory human review, not evidence that model-proposed tests cover the goal.
    """
    spec=draft_spec(llm,goal,context)
    if not spec:
        return '',[{'severity':'high','issue':'spec output incomplete after bounded retry','evidence':'No complete spec with checks returned.'}],[]
    findings=[]
    for round_index in range(max_rounds):
        checks=extract_checks(spec)
        bad=invalid_checks(checks,workdir,declared_outputs(spec))
        findings=goldfish_review(llm,spec,workdir)+bad
        if not any(f.get('severity')=='high' for f in findings):break
        revision=_request_spec(llm,'Revise this spec to resolve the findings. Preserve the goal and return complete compact JSON. '
                               'Checks may invoke declared output files after implementation, but not missing external test scripts.\nORIGINAL GOAL:\n'+goal+'\nSPEC:\n'+spec+'\nFINDINGS:\n'+json.dumps(findings))
        if revision is None:
            findings.append({'severity':'high','issue':'revision incomplete after bounded retry; retained previous complete spec',
                             'evidence':'No replacement accepted.'})
            break
        spec=revision
    checks=extract_checks(spec)
    bad=invalid_checks(checks,workdir,declared_outputs(spec))
    return spec,findings+bad,[] if bad else checks
