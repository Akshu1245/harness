import json
from rashi import egm


def test_goldfish_sees_only_spec_and_files(tmp_path):
    (tmp_path / "a.py").write_text("x=1")
    seen = []
    def llm(sys, user):
        seen.append(user); return '{"findings":[]}'
    egm.goldfish_review(llm, "Goal\n- `a.py`\n", str(tmp_path))
    assert "x=1" in seen[0] and "Project context" not in seen[0]


def test_unparsable_reviewer_is_high_finding(tmp_path):
    f = egm.goldfish_review(lambda s, u: "lol", "spec", str(tmp_path))
    assert f[0]["severity"] == "high"


def test_spec_gate_revises_then_extracts_checks(tmp_path):
    calls = []
    def llm(sys, user):
        calls.append(sys)
        if sys == egm.GOLDFISH_SYS:
            n = calls.count(egm.GOLDFISH_SYS)
            return json.dumps({"findings": [{"severity": "high" if n == 1 else "low", "issue": "no check", "evidence": ""}]})
        return "Goal\nChecks\n- `pytest -q`\n"
    spec, findings, checks = egm.spec_gate(llm, "g", str(tmp_path))
    assert checks == [{"id": "c1", "cmd": "pytest -q"}]
    assert calls.count(egm.ELEPHANT_SYS) == 2


def test_drift(tmp_path):
    (tmp_path / "ok.py").write_text("")
    r = egm.drift_report("`ok.py` `gone.py`", str(tmp_path))
    assert r["missing_paths"] == ["gone.py"]


def test_checks_on_missing_files_are_rejected(tmp_path):
    (tmp_path / "t.py").write_text("")
    bad = lambda s, u: '{"findings":[]}' if s == egm.GOLDFISH_SYS else "Checks\n- `python -m pytest t.py nope.py`\n"
    spec, findings, checks = egm.spec_gate(bad, "g", str(tmp_path))
    assert checks == [] and any("nope.py" in f["issue"] for f in findings)
    good = lambda s, u: '{"findings":[]}' if s == egm.GOLDFISH_SYS else "Checks\n- `python -m pytest t.py`\n"
    assert egm.spec_gate(good, "g", str(tmp_path))[2] != []


def test_revision_that_drops_checks_keeps_last_valid(tmp_path):
    (tmp_path / "t.py").write_text("")
    n = {"g": 0}
    def llm(s, u):
        if s == egm.GOLDFISH_SYS:
            n["g"] += 1
            return '{"findings":[{"severity":"high","issue":"x","evidence":""}]}'
        return "Checks\n- `python t.py`\n" if "Revise" not in u else "no checks here"
    spec, findings, checks = egm.spec_gate(llm, "g", str(tmp_path))
    assert checks == [{"id": "c1", "cmd": "python t.py"}]


def test_goldfish_retries_once_on_unparsable(tmp_path):
    calls = {"n": 0}
    def llm(s, u):
        calls["n"] += 1
        return "lol" if calls["n"] == 1 else '{"findings":[{"severity":"low","issue":"ok"}]}'
    f = egm.goldfish_review(llm, "spec", str(tmp_path))
    assert f == [{"severity": "low", "issue": "ok"}] and calls["n"] == 2


def test_draft_spec_retries_an_empty_reply():
    """Dogfood 2026-11-13: Kenari's flash model answered a spec prompt with an empty
    message; the draft must ask once more instead of flowing an empty spec downstream."""
    calls = []

    def llm(system, user):
        calls.append(user)
        return "" if len(calls) == 1 else "Spec\n- `test -f x.py`"

    from rashi.egm import draft_spec
    assert draft_spec(llm, "make x") == "Spec\n- `test -f x.py`"
    assert len(calls) == 2 and "previous reply was empty" in calls[1]


def test_brainstorm_brief_then_challenge_revision():
    """EGM brainstorm: elephant drafts a brief, fresh goldfish challenges it, elephant
    revises once when the challenge has a high finding."""
    calls = []
    def llm(system, user):
        calls.append(system)
        if system == egm.CHALLENGE_SYS:
            return '{"findings":[{"severity":"high","issue":"fuzzy goal","evidence":"no metric"}]}'
        return "Problem\nx\n" if "Revise" not in user else "Problem\nx revised\n"
    brief, findings = egm.brainstorm(llm, "idea")
    assert brief.endswith("revised\n") and findings[0]["issue"] == "fuzzy goal"
    assert calls == [egm.BRIEF_SYS, egm.CHALLENGE_SYS, egm.BRIEF_SYS]


def test_brainstorm_keeps_brief_when_challenge_is_low():
    def llm(system, user):
        return '{"findings":[{"severity":"low","issue":"nit","evidence":""}]}' if system == egm.CHALLENGE_SYS \
            else "Problem\nx\n"
    brief, _ = egm.brainstorm(llm, "idea")
    assert brief == "Problem\nx\n"


def test_brainstorm_retries_empty_reply():
    calls = []
    def llm(system, user):
        calls.append(user)
        if system == egm.CHALLENGE_SYS:
            return '{"findings":[]}'
        return "" if len(calls) == 1 else "Problem\nx\n"
    brief, _ = egm.brainstorm(llm, "idea")
    assert brief == "Problem\nx\n" and "previous reply was empty" in calls[1]


def structured_spec(check='test -f out.py'):
    return json.dumps({'goal':'make out','constraints':['stdlib'],'files':['out.py'],
                       'checks':[check],'out_of_scope':['network']})


def test_structured_spec_roundtrips_exact_commands():
    command='python -c "assert 1 == 1"'
    spec=egm.draft_spec(lambda s,u:structured_spec(command),'g')
    assert egm.extract_checks(spec)==[{'id':'c1','cmd':command}]
    assert 'out.py' in spec and 'network' in spec


def test_replayed_truncated_and_empty_live_specs_never_yield_checks(tmp_path):
    from pathlib import Path
    records=json.loads((Path(__file__).parent/'fixtures/truncated_spec_responses.json').read_text())
    for response in records:
        # Reviewer JSON and empty/truncated draft/revision are not complete execution specs.
        assert egm._complete_spec(response) is None
        spec,findings,checks=egm.spec_gate(lambda s,u:response,'g',str(tmp_path))
        assert spec=='' and checks==[] and findings[0]['severity']=='high'


def test_invalid_structured_draft_gets_only_one_retry():
    calls=[]
    def llm(s,u):
        calls.append(u)
        return '{"goal":"cut off' if len(calls)==1 else structured_spec()
    spec=egm.draft_spec(llm,'g')
    assert len(calls)==2 and egm.extract_checks(spec)


def test_empty_revision_retains_matching_spec_and_high_finding(tmp_path):
    calls=[]
    def llm(s,u):
        calls.append(s)
        if s==egm.GOLDFISH_SYS:return '{"findings":[{"severity":"high","issue":"review"}]}'
        return '' if 'Revise' in u else structured_spec()
    spec,findings,checks=egm.spec_gate(llm,'g',str(tmp_path))
    assert spec and checks==egm.extract_checks(spec)
    assert any('revision incomplete' in f['issue'] for f in findings)
    assert calls.count(egm.ELEPHANT_SYS)==3  # draft + two revision attempts


def test_partial_json_and_open_shell_quotes_refused():
    assert egm._complete_spec('{"goal":"g","checks":["true"]') is None
    assert egm._complete_spec(structured_spec('python -c "unfinished')) is None
    assert egm._complete_spec('Checks\n- `true`\n```python\ncut off') is None


def test_explicit_truncation_retries_but_provider_errors_do_not():
    n=[]
    def llm(s,u):
        n.append(u)
        if len(n)==1:raise egm.IncompleteModelOutput('length')
        return structured_spec()
    assert egm.draft_spec(llm,'g') and len(n)==2
    import pytest
    with pytest.raises(RuntimeError,match='quota'):
        egm.draft_spec(lambda s,u:(_ for _ in ()).throw(RuntimeError('quota')),'g')


def test_checks_can_execute_declared_implementation_after_it_is_built(tmp_path):
    def llm(s,u):
        if s==egm.GOLDFISH_SYS:return '{"findings":[]}'
        return structured_spec('python -m py_compile out.py')
    spec,findings,checks=egm.spec_gate(llm,'g',str(tmp_path))
    assert checks and not findings
    assert egm.invalid_checks([{'id':'x','cmd':'python missing_test.py'}],str(tmp_path),egm.declared_outputs(spec))


def test_declared_outputs_do_not_include_commands_or_traversal():
    assert egm.declared_outputs('# Files\n- `app.py`\n- `../escape.py`\n## Checks\n- `python fake_test.py`')=={'app.py'}


def test_reviewer_length_truncation_is_bounded_high_finding(tmp_path):
    calls=[]
    def truncated(s,u):
        calls.append(u)
        raise egm.IncompleteModelOutput('length')
    findings=egm.goldfish_review(truncated,'spec',str(tmp_path))
    assert len(calls)==2 and findings[0]['severity']=='high'
    assert 'truncated' in findings[0]['evidence']


def test_reviewer_recovers_after_explicit_truncation(tmp_path):
    calls=[]
    def llm(s,u):
        calls.append(u)
        if len(calls)==1:raise egm.IncompleteModelOutput('length')
        return '{"findings":[]}'
    assert egm.goldfish_review(llm,'spec',str(tmp_path))==[]
    assert len(calls)==2
