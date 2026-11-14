"""Caller-owned acceptance, one workdir. Models propose specs, never rewrite the contract.
These are cooperative checks, not containment against hostile processes.
"""
import copy
import hashlib
import json
from pathlib import Path

from . import egm
from .loop import digest,run_loop
from .orchestrate import CliAgent


def validate(contract,workdir):
    if not isinstance(contract,dict):raise ValueError('contract must be an object')
    checks=contract.get('checks')
    if (not isinstance(checks,list) or not checks or
        any(not isinstance(c,dict) or not isinstance(c.get('id'),str) or not c['id'] or
            not isinstance(c.get('cmd'),str) or not c['cmd'].strip() for c in checks) or
        len({c['id'] for c in checks})!=len(checks)):
        raise ValueError('contract requires nonempty unique-id checks')
    protected=contract.get('protected',[])
    if not isinstance(protected,list) or any(not isinstance(p,str) or not p for p in protected):
        raise ValueError('protected must be a list of relative paths')
    root=Path(workdir).resolve()
    for rel in protected:
        path=Path(rel)
        if path.is_absolute() or '..' in path.parts:raise ValueError('unsafe protected path')
        target=root
        for part in path.parts:
            target=target/part
            if target.is_symlink():raise ValueError('protected path cannot contain symlinks')
        if not target.is_file():raise ValueError('missing protected acceptance fixture: '+rel)
    return {'checks':copy.deepcopy(checks),'protected':list(protected)}


def build(goal,workdir,llm,approve,agents,contract,max_iters=6):
    """No planner decomposition: original goal + immutable checks run in this workdir."""
    frozen=validate(contract,workdir)
    baseline=digest(workdir,frozen['protected'])
    scope=json.dumps({'goal':goal,'workdir':str(Path(workdir).resolve()),**frozen,
                      'protected_sha256':baseline,'max_iters':max_iters},sort_keys=True)
    identity=hashlib.sha256(scope.encode()).hexdigest()
    if not agents:return {'status':'NO_READY_AGENTS','mode':'caller_contract','contract_sha256':identity}
    # Stable single-agent selection, explicitly shown before approval. Not a parallel build.
    name=sorted(agents)[0]
    agent=agents[name]
    command=agent if isinstance(agent,list) else 'in-process agent'
    context='CALLER CONTRACT (cannot be removed or relaxed):\n'+scope
    try:
        spec,findings,_=egm.spec_gate(llm,goal,workdir,context=context)
    except Exception as error:
        return {'status':'FAILED_PLANNING','mode':'caller_contract','error_type':type(error).__name__,
                'contract_sha256':identity}
    if not spec:return {'status':'NO_COMPLETE_SPEC','findings':findings,'mode':'caller_contract'}
    review=(spec+'\n\nCALLER-OWNED EXECUTION CONTRACT (authoritative over proposed spec):\n'+scope+
            '\nContract SHA-256: '+identity+'\nAgent: '+name+' '+json.dumps(command)+
            '\nMode: single workdir, no model task splitting.\n'
            'Warning: coding agent uses host permissions; checks are not a security sandbox.')
    if not approve(review,findings):return {'status':'SPEC_NOT_APPROVED','mode':'caller_contract'}
    # Validate again after review; even an accidental edit while the dialog is open invalidates it.
    validate(frozen,workdir)
    if digest(workdir,frozen['protected'])!=baseline:
        return {'status':'FAILED_CONTRACT_CHANGED','mode':'caller_contract'}
    if not callable(agent):agent=CliAgent(agent)
    status,log=run_loop({'goal':goal+'\n\nRequired acceptance contract:\n'+scope,
                         'workdir':str(workdir),'checks':frozen['checks'],
                         'protected':frozen['protected'],'max_iters':max_iters},agent)
    return {'status':status,'mode':'caller_contract','contract_sha256':identity,
            'agent':name,'iterations':len(log),'findings':findings}
