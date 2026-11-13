"""Small HumanEval subset adapter, not an official leaderboard implementation.

Loads a caller-supplied MIT HumanEval JSONL(.gz), never downloads or executes on import.
One completion per task, no test feedback, exact selected IDs and data hash recorded.
Generation sees prompt only, never canonical solutions or private tests.
Evaluation requires Linux bwrap and creates a fresh filesystem namespace with only runtime
paths and the disposable grader directory. No host home, environment credentials or network.
This is defense in depth, not a claim of resistance to malicious kernel exploits or benchmark
cheating. Run on a disposable host. Canonical self-tests are calibration, NOT model scores.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid


def load_tasks(path, limit=3):
    if not 1 <= limit <= 164:
        raise ValueError('limit must be 1..164')
    opener = gzip.open if str(path).endswith('.gz') else open
    rows, seen = [], set()
    with opener(path, 'rt') as f:
        for line in f:
            row = json.loads(line)
            if not all(isinstance(row.get(k), str) for k in ('task_id','prompt','test','entry_point')):
                raise ValueError('invalid HumanEval row')
            if row['task_id'] in seen:
                raise ValueError('duplicate task id')
            seen.add(row['task_id'])
            rows.append(row)
            if len(rows) == limit:
                break
    if len(rows) != limit:
        raise ValueError('dataset shorter than requested subset')
    return rows


def isolation_argv(directory):
    if not shutil.which('bwrap'):
        raise RuntimeError('bwrap required; refusing unsandboxed benchmark execution')
    argv = ['bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv',
            '--setenv','PATH','/usr/bin:/bin','--tmpfs','/','--proc','/proc','--dev','/dev',
            '--tmpfs','/tmp']
    # A new root: no read-only bind of the host root (which exposes private readable files).
    for runtime in ('/usr','/lib','/lib64','/bin'):
        if Path(runtime).exists():
            argv += ['--ro-bind',runtime,runtime]
    return argv + ['--ro-bind',str(directory),'/work','--chdir','/work']


def grade(task, completion, timeout=8):
    marker = 'RASHI_TESTS_PASSED_' + uuid.uuid4().hex
    program = task['prompt'] + completion + '\n' + task['test'] + '\ncheck(' + task['entry_point'] + ')\n'
    bootstrap = '''import resource
resource.setrlimit(resource.RLIMIT_CPU, (3,3))
resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024,512*1024*1024))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024*1024,1024*1024))
resource.setrlimit(resource.RLIMIT_NOFILE, (64,64))
resource.setrlimit(resource.RLIMIT_NPROC, (16,16))
'''
    with tempfile.TemporaryDirectory(prefix='rashi-eval-') as d:
        Path(d,'grade.py').write_text(bootstrap + 'exec(' + repr(program) + ')\nprint(' + repr(marker) + ')\n')
        argv = isolation_argv(d) + ['/usr/bin/python3','-I','-S','/work/grade.py']
        with tempfile.TemporaryFile() as log:
            try:
                p = subprocess.run(argv, env={}, stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                                   start_new_session=True)
            except subprocess.TimeoutExpired:
                return {'passed':False,'status':'TIMEOUT'}
            log.seek(0)
            output = log.read(1024*1024).decode(errors='replace')
        passed = p.returncode == 0 and marker in output.splitlines()
        return {'passed':passed, 'status':'PASS' if passed else 'FAIL', 'exit_code':p.returncode}


def evaluate(tasks, samples, dataset_hash, kind='model'):
    # Exactly one attempt per selected task. Missing samples count as failure, never disappear
    # from the denominator. Reject duplicates upstream instead of picking a favorable sample.
    selected = {t['task_id'] for t in tasks}
    if set(samples) - selected:
        raise ValueError('samples contain unselected task ids')
    results = []
    for task in tasks:
        tid = task['task_id']
        result = grade(task, samples[tid]) if tid in samples else {'passed':False,'status':'MISSING'}
        results.append({'task_id':tid, **result})
    passed = sum(r['passed'] for r in results)
    return {'benchmark':'HumanEval custom ordered subset', 'kind':kind,
            'official_score':False, 'dataset_sha256':dataset_hash, 'task_ids':[t['task_id'] for t in tasks],
            'attempts_per_task':1, 'passed':passed, 'total':len(tasks),
            'subset_pass_fraction':passed/len(tasks), 'results':results}


def generate(tasks, llm):
    system = ('Complete the provided Python function. Return only its indented body, no markdown, '
              'no repeated signature. Do not run tools. Do not claim tests passed.')
    return {t['task_id']:llm(system,t['prompt']) for t in tasks}


def main(args):
    tasks = load_tasks(args.data, args.limit)
    # Preflight isolation before contacting any model.
    probe = grade({'prompt':'','test':'def check(f): assert f() == 1', 'entry_point':'f'},
                  'def f(): return 1\n')
    if not probe['passed']:
        raise RuntimeError('benchmark sandbox preflight failed')
    if args.self_test:
        good = {t['task_id']:t['canonical_solution'] for t in tasks}
        bad = {t['task_id']:'    raise AssertionError("calibration mutant")\n' for t in tasks}
        digest = hashlib.sha256(Path(args.data).read_bytes()).hexdigest()
        report = {'kind':'calibration_only_not_model_score',
                  'reference':evaluate(tasks,good,digest,'reference_calibration'),
                  'broken':evaluate(tasks,bad,digest,'broken_calibration')}
    else:
        if args.generate:
            from .__main__ import find_llm, make_llm
            found = find_llm()
            if not found:
                raise RuntimeError('no verified free default model configured')
            samples = generate(tasks, make_llm(*found))
            sample_path = Path(str(args.out) + '.samples.jsonl')
            sample_path.write_text(''.join(json.dumps({'task_id':tid,'completion':code}) + '\n'
                                           for tid,code in samples.items()))
        else:
            if not args.samples:
                raise ValueError('--samples or --generate required')
            samples = {}
            with open(args.samples) as f:
                for line in f:
                    row = json.loads(line)
                    if row['task_id'] in samples or not isinstance(row.get('completion'), str):
                        raise ValueError('duplicate sample or non-string completion')
                    samples[row['task_id']] = row['completion']
        digest = hashlib.sha256(Path(args.data).read_bytes()).hexdigest()
        report = evaluate(tasks,samples,digest)
        if args.generate:
            report['provider'], report['model'] = found[:2]
            report['samples_file'] = str(sample_path)
    Path(args.out).write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return 0
