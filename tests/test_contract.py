import json
from pathlib import Path
import pytest
from rashi.build import one_press


def planner(s,u):
    if 'fresh reviewer' in s:return '{"findings":[]}'
    # Intentionally wrong spec checks and goal. Caller-owned contract still decides.
    return json.dumps({'goal':'unrelated','constraints':[],'files':['out.txt'],
                       'checks':['true'],'out_of_scope':[]})


def setup_contract(tmp_path):
    (tmp_path/'accept.py').write_text("from pathlib import Path\nassert Path('out.txt').read_text()=='required'\n")
    return {'checks':[{'id':'accept','cmd':'python accept.py'}],'protected':['accept.py']}


def test_caller_checks_and_goal_survive_model_omission(tmp_path):
    c=setup_contract(tmp_path);seen=[]
    def approve(review,findings):
        assert 'ORIGINAL GOAL' in review and 'python accept.py' in review
        assert 'single workdir' in review
        c['checks'][0]['cmd']='true'  # external mutable object cannot change frozen review
        return True
    def agent(g,f,w):
        seen.append(g);assert Path(w)==tmp_path
        Path(w,'out.txt').write_text('required')
    r=one_press('ORIGINAL GOAL',str(tmp_path),planner,approve,agents={'one':agent},acceptance=c)
    assert r['status']=='DONE_VERIFIED' and r['mode']=='caller_contract'
    assert 'ORIGINAL GOAL' in seen[0] and 'python accept.py' in seen[0]
    assert not (tmp_path/'t1').exists()


def test_failed_acceptance_cannot_be_model_done(tmp_path):
    c=setup_contract(tmp_path)
    def wrong(g,f,w):Path(w,'out.txt').write_text('wrong')
    r=one_press('g',str(tmp_path),planner,lambda s,f:True,agents={'one':wrong},acceptance=c,max_iters=1)
    assert r['status']=='STOPPED_MAX_ITERS'


def test_denial_never_invokes_agent(tmp_path):
    c=setup_contract(tmp_path)
    def forbidden(*a):raise AssertionError('agent must not run')
    r=one_press('g',str(tmp_path),planner,lambda s,f:False,agents={'one':forbidden},acceptance=c)
    assert r['status']=='SPEC_NOT_APPROVED'


def test_fixture_change_during_review_refuses(tmp_path):
    c=setup_contract(tmp_path)
    def approve(s,f):(tmp_path/'accept.py').write_text('pass');return True
    r=one_press('g',str(tmp_path),planner,approve,agents={'one':lambda *a:None},acceptance=c)
    assert r['status']=='FAILED_CONTRACT_CHANGED'


def test_agent_cannot_rewrite_acceptance_to_pass(tmp_path):
    c=setup_contract(tmp_path)
    def cheat(g,f,w):Path(w,'accept.py').write_text('pass')
    r=one_press('g',str(tmp_path),planner,lambda s,f:True,agents={'one':cheat},acceptance=c,max_iters=1)
    assert r['status']=='FAILED_TAMPERED_PROTECTED_FILES'


def test_missing_fixture_fails_before_model_or_agent(tmp_path):
    c=setup_contract(tmp_path);(tmp_path/'accept.py').unlink()
    def forbidden(*a):raise AssertionError('must fail before model')
    with pytest.raises(ValueError,match='missing protected'):
        one_press('g',str(tmp_path),forbidden,forbidden,agents={'one':forbidden},acceptance=c)


def test_contract_rejects_empty_duplicate_checks_and_symlink(tmp_path):
    from rashi.contract import validate
    for checks in [[],[{'id':'x','cmd':'true'},{'id':'x','cmd':'false'}]]:
        with pytest.raises(ValueError):validate({'checks':checks},tmp_path)
    (tmp_path/'link').symlink_to('/etc/passwd')
    with pytest.raises(ValueError,match='symlink'):
        validate({'checks':[{'id':'x','cmd':'true'}],'protected':['link']},tmp_path)


def test_provider_failure_is_reported_without_agent_execution(tmp_path):
    c=setup_contract(tmp_path)
    def unavailable(*a):raise TimeoutError('provider')
    r=one_press('g',str(tmp_path),unavailable,lambda s,f:True,agents={'one':lambda *a:None},acceptance=c)
    assert r['status']=='FAILED_PLANNING' and r['error_type']=='TimeoutError'
