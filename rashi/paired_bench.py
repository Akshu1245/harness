"""Paired custom HumanEval study, NOT an official benchmark protocol.

Both arms share the first completion. Rashi repairs using ONLY doctest examples in the
prompt. Hidden tests are consulted once per final arm, never for repair or selection.
Optional independent-sampling control gets the same maximum call budget, selects by visible
examples only. Report actual calls: early stopping means budgets may differ in practice.
"""
import ast
import hashlib
import json
from pathlib import Path
import time

from .public_bench import grade, load_tasks

BODY_SYS = ('Complete the Python function. Return only its indented body, no markdown or '
            'repeated signature. Do not claim tests passed.')


def visible_probe(task, completion, grader=grade):
    # testmod sees the candidate function's prompt docstring, not benchmark hidden tests.
    # Use doctest.run_docstring_examples with an explicit checker to count tested examples.
    try:
        tree = ast.parse(task['prompt'] + '    pass\n')
        fn = next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)))
        doc = ast.get_docstring(fn) or ''
    except (SyntaxError,StopIteration):
        doc = ''
    import doctest
    examples = doctest.DocTestParser().get_examples(doc)
    probe = dict(task)
    probe['test'] = '''def check(candidate):
    import doctest
    parser = doctest.DocTestParser()
    test = parser.get_doctest(__import__('inspect').cleandoc(candidate.__doc__ or ''),
                              dict(candidate.__globals__, **{candidate.__name__: candidate}),
                              'visible', None, None)
    runner = doctest.DocTestRunner()
    runner.run(test)
    assert runner.failures == 0
'''
    result = grader(probe,completion)
    return {**result,'visible_examples':len(examples),
            'feedback_source':'prompt_doctests_only' if examples else 'syntax_execution_only'}


def paired(tasks,llm,dataset_hash,max_attempts=2,control=False,grader=grade):
    if not 1 <= max_attempts <= 4:
        raise ValueError('max_attempts must be 1..4')
    rows=[]
    for task in tasks:
        began=time.monotonic()
        errors=[]
        def call(system,user):
            try:
                return llm(system,user) or ''
            except Exception as ex:
                errors.append(type(ex).__name__)
                return ''
        initial=call(BODY_SYS,task['prompt'])
        chosen=initial
        calls=1
        probes=[]
        for attempt in range(max_attempts):
            probe=visible_probe(task,chosen,grader)
            probes.append(probe)
            if probe['passed'] or calls >= max_attempts:
                break
            feedback=('The candidate failed prompt-visible examples or syntax/execution checks. '
                      f"Status: {probe['status']}. No hidden tests were consulted. "
                      'Inspect the previous code, identify an error, and return a corrected body only.')
            chosen=call(BODY_SYS,task['prompt']+'\nPrevious body:\n'+chosen+'\n'+feedback)
            calls+=1
        # All generation/selection is complete before the official hidden grader is used.
        control_body=initial
        control_calls=1
        if control:
            passing=visible_probe(task,initial,grader)['passed']
            for _ in range(max_attempts-1):
                candidate=call(BODY_SYS,task['prompt'])
                control_calls+=1
                if visible_probe(task,candidate,grader)['passed'] and not passing:
                    control_body=candidate; passing=True
        bare=grader(task,initial)
        enhanced=grader(task,chosen)
        row={'task_id':task['task_id'],'bare':bare,'rashi':enhanced,
             'calls':{'bare':1,'rashi':calls},'visible_probes':probes,'errors':errors,
             'samples':{'bare':initial,'rashi':chosen},'elapsed_seconds':round(time.monotonic()-began,3)}
        if control:
            row['independent_control']=grader(task,control_body)
            row['calls']['independent_control']=control_calls
            row['samples']['independent_control']=control_body
        rows.append(row)
    total=len(tasks)
    if total == 0:raise ValueError('no tasks')
    bare=sum(r['bare']['passed'] for r in rows)
    enhanced=sum(r['rashi']['passed'] for r in rows)
    wins=sum(not r['bare']['passed'] and r['rashi']['passed'] for r in rows)
    losses=sum(r['bare']['passed'] and not r['rashi']['passed'] for r in rows)
    return {'study':'custom paired HumanEval subset','official_score':False,
            'dataset_sha256':dataset_hash,'total':total,'bare_passed':bare,'rashi_passed':enhanced,
            'lift_percentage_points':100*(enhanced-bare)/total,'paired_wins':wins,'paired_losses':losses,
            'max_attempts':max_attempts,'same_initial_completion':True,
            'equal_compute_claim':False,'selection_feedback':'prompt doctests, never hidden tests',
            'caveats':['Small ordered subset is not representative; no significance claim.',
                       'Shared first answer reduces baseline variance; extra repair calls are disclosed.',
                       'Passing visible examples does not prove hidden correctness.'], 'rows':rows}


def main(args):
    tasks=load_tasks(args.data,args.limit)
    # Check isolation before any provider request.
    preflight=grade({'prompt':'','entry_point':'f','test':'def check(f): assert f()==1'},'def f(): return 1\n')
    if not preflight['passed']: raise RuntimeError('sandbox preflight failed')
    from .__main__ import find_llm,make_llm
    found=find_llm()
    if not found:raise RuntimeError('no free default model configured')
    report=paired(tasks,make_llm(*found),hashlib.sha256(Path(args.data).read_bytes()).hexdigest(),
                  max_attempts=args.max_attempts,control=args.control)
    report['provider'],report['model']=found[:2]
    Path(args.out).write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != 'rows'},indent=2))
    return 0
