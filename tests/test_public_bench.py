import json
import shutil
import pytest
from rashi import public_bench as pb


def task():
    return {'task_id':'test/0','prompt':'def f():\n','test':'def check(f): assert f() == 1',
            'entry_point':'f'}


def test_generation_sees_prompt_not_tests_or_gold():
    row = task(); row['canonical_solution'] = 'SECRET_GOLD'
    seen = []
    def llm(system,user):
        seen.append(user)
        return '    return 1\n'
    assert pb.generate([row],llm) == {'test/0':'    return 1\n'}
    assert seen == [row['prompt']]


def test_missing_samples_stay_in_denominator(monkeypatch):
    monkeypatch.setattr(pb,'grade',lambda *a: {'passed':True,'status':'PASS'})
    t2 = dict(task(), task_id='test/1')
    r = pb.evaluate([task(),t2],{'test/0':'answer'},'sha')
    assert (r['passed'],r['total'],r['subset_pass_fraction']) == (1,2,0.5)
    assert r['results'][1]['status'] == 'MISSING' and not r['official_score']


def test_refuse_unavailable_sandbox(monkeypatch):
    monkeypatch.setattr(pb.shutil,'which',lambda *a: None)
    with pytest.raises(RuntimeError,match='refusing unsandboxed'):
        pb.isolation_argv('/tmp')


def test_load_tasks_validation(tmp_path):
    p = tmp_path / 'dataset.jsonl'
    p.write_text(json.dumps(task())+'\n')
    assert pb.load_tasks(p,1)[0]['task_id'] == 'test/0'
    with pytest.raises(ValueError,match='shorter'):
        pb.load_tasks(p,2)


@pytest.mark.skipif(not shutil.which('bwrap'),reason='requires bwrap')
def test_live_grader_accepts_correct_rejects_broken_and_early_exit():
    assert pb.grade(task(),'    return 1\n')['passed']
    assert not pb.grade(task(),'    return 2\n')['passed']
    assert not pb.grade(task(),'    import os; os._exit(0)\n')['passed']


@pytest.mark.skipif(not shutil.which('bwrap'),reason='requires bwrap')
def test_grader_hides_host_home_and_credentials(tmp_path,monkeypatch):
    secret = tmp_path/'private.txt'; secret.write_text('private')
    monkeypatch.setenv('RASHI_TEST_CREDENTIAL','not-for-candidate')
    completion = ('    import os\n'
                  '    assert "RASHI_TEST_CREDENTIAL" not in os.environ\n'
                  f'    assert not os.path.exists({str(secret)!r})\n'
                  '    return 1\n')
    assert pb.grade(task(),completion)['passed']
