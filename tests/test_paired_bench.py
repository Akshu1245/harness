from rashi.paired_bench import paired, visible_probe


def task():
    return {'task_id':'x','prompt':'def f():\n    """>>> f()\n    1\n    """\n',
            'test':'SECRET_HIDDEN','entry_point':'f'}


def test_repair_never_sees_hidden_tests_and_fixed_denominator():
    seen=[]
    def llm(system,user):
        seen.append(user)
        return '    return 0\n' if len(seen)==1 else '    return 1\n'
    graded=[]
    def grader(t,c):
        graded.append(t['test'])
        return {'passed':'return 1' in c,'status':'PASS' if 'return 1' in c else 'FAIL'}
    r=paired([task()],llm,'hash',grader=grader)
    assert r['total']==1 and r['bare_passed']==0 and r['rashi_passed']==1
    assert r['lift_percentage_points']==100 and not r['equal_compute_claim']
    assert all('SECRET_HIDDEN' not in u for u in seen)
    assert graded[-2:]==['SECRET_HIDDEN','SECRET_HIDDEN']
    assert r['rows'][0]['calls']=={'bare':1,'rashi':2}


def test_independent_control_has_same_max_budget_not_hidden_selection():
    def grader(t,c):return {'passed':False,'status':'FAIL'}
    r=paired([task()],lambda *a:'    return 0\n','h',max_attempts=3,control=True,grader=grader)
    assert r['rows'][0]['calls']=={'bare':1,'rashi':3,'independent_control':3}
    assert r['lift_percentage_points']==0


def test_model_failure_is_retained_in_denominator():
    def dead(*a):raise TimeoutError()
    r=paired([task()],dead,'h',grader=lambda *a:{'passed':False,'status':'FAIL'})
    assert r['total']==1 and r['bare_passed']==r['rashi_passed']==0
    assert r['rows'][0]['errors']==['TimeoutError','TimeoutError']


def test_real_visible_probe_uses_prompt_examples_not_hidden():
    import shutil,pytest
    if not shutil.which('bwrap'):pytest.skip('bwrap required')
    assert visible_probe(task(),'    return 1\n')['passed']
    assert not visible_probe(task(),'    return 0\n')['passed']
