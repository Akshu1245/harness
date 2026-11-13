import hashlib
import io
import json
from rashi.approval_bridge import request,approval_text
from rashi import build,mcp_server


def test_pipe_approval_is_bound_to_exact_review():
    review=approval_text('spec',[])
    digest=hashlib.sha256(review.encode()).hexdigest()
    output=io.StringIO()
    assert request('spec',[],io.StringIO(json.dumps({'decision':'approve','sha256':digest})+'\n'),output)
    assert json.loads(output.getvalue())['review']==review
    assert not request('spec',[],io.StringIO('{"decision":"approve","sha256":"other"}\n'),io.StringIO())
    assert not request('spec',[],io.StringIO(''),io.StringIO())


def fake_llm(system,user):
    if 'fresh reviewer' in system:return '{"findings":[]}'
    if 'Split this spec' in system:return '{"tasks":[{"id":"one","goal":"make out","checks":["test -f out"]}]}'
    return 'Goal\nChecks\n- `test -f out`\n'


def test_final_checks_and_task_directories_are_shown_before_approval(tmp_path):
    calls=[]
    def llm(s,u):calls.append(s);return fake_llm(s,u)
    def approve(review,findings):
        assert 'test -f out' in review and '"id": "one"' in review
        assert str(tmp_path.resolve()) in review
        calls.append('APPROVED');return True
    r=build.one_press('g',str(tmp_path),llm,approve,agents={'fake':lambda g,f,w:__import__('pathlib').Path(w,'out').write_text('ok')})
    assert r['status']=='DONE_VERIFIED'
    assert calls[-1]=='APPROVED'  # no planning/model calls after scope approval


def exercise_mcp(tmp_path,monkeypatch,action,capability=True):
    from rashi import __main__ as main
    monkeypatch.setattr(main,'find_llm',lambda:('kenari','glm-4-7-flash:free','fake'))
    monkeypatch.setattr(main,'make_llm',lambda *a:fake_llm)
    monkeypatch.setattr(build,'detect_all',lambda:{})
    calls=[]
    def agent(g,f,w):calls.append(w);__import__('pathlib').Path(w,'out').write_text('ok')
    monkeypatch.setattr(build,'ready_agents',lambda *a:{'fake':agent})
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'capabilities':{'elicitation':{'form':{}}} if capability else {}}},
              {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'rashi_build','arguments':{'goal':'g','dir':str(tmp_path)}}}]
    if capability:messages.append({'jsonrpc':'2.0','id':'rashi-approval-1','result':{'action':action,'content':{'approve':True}}})
    messages.append({'jsonrpc':'2.0','id':3,'method':'ping'})
    output=io.StringIO()
    mcp_server.serve(io.StringIO(''.join(json.dumps(m)+'\n' for m in messages)),output)
    return [json.loads(l) for l in output.getvalue().splitlines()],calls


def test_mcp_accept_executes_exact_plan_then_answers_ping(tmp_path,monkeypatch):
    events,calls=exercise_mcp(tmp_path,monkeypatch,'accept')
    ask=next(m for m in events if m.get('method')=='elicitation/create')
    assert 'test -f out' in ask['params']['message'] and '"id": "one"' in ask['params']['message']
    result=next(m['result'] for m in events if m.get('id')==2)
    assert json.loads(result['content'][0]['text'])['status']=='DONE_VERIFIED' and len(calls)==1
    assert events[-1]['id']==3


def test_mcp_decline_or_missing_capability_never_runs_agent(tmp_path,monkeypatch):
    for action,cap in [('decline',True),('cancel',True),('accept',False)]:
        events,calls=exercise_mcp(tmp_path,monkeypatch,action,cap)
        assert calls==[]
        result=next(m['result'] for m in events if m.get('id')==2)
        assert result['isError']


def test_mcp_legacy_protocol_never_elicits(tmp_path,monkeypatch):
    from rashi import __main__ as main
    monkeypatch.setattr(main,'find_llm',lambda:('kenari','glm-4-7-flash:free','fake'))
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{'elicitation':{}}}},
              {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'rashi_build','arguments':{'goal':'g','dir':str(tmp_path)}}}]
    output=io.StringIO()
    mcp_server.serve(io.StringIO(''.join(json.dumps(m)+'\n' for m in messages)),output)
    result=[json.loads(l) for l in output.getvalue().splitlines()]
    assert result[0]['result']['protocolVersion']=='2024-11-05'
    assert result[1]['result']['isError'] and len(result)==2


def test_mcp_eof_during_approval_denies_without_hanging(tmp_path,monkeypatch):
    from rashi import __main__ as main
    monkeypatch.setattr(main,'find_llm',lambda:('kenari','glm-4-7-flash:free','fake'))
    monkeypatch.setattr(main,'make_llm',lambda *a:fake_llm)
    monkeypatch.setattr(build,'detect_all',lambda:{})
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{'elicitation':{}}}},
              {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'rashi_build','arguments':{'goal':'g','dir':str(tmp_path)}}}]
    output=io.StringIO()
    mcp_server.serve(io.StringIO(''.join(json.dumps(m)+'\n' for m in messages)),output)
    result=[json.loads(l) for l in output.getvalue().splitlines()]
    assert len(result)==3 and result[-1]['result']['isError']
    assert json.loads(result[-1]['result']['content'][0]['text'])['status']=='SPEC_NOT_APPROVED'
