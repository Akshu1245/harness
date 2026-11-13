#!/usr/bin/env python3
"""No-model fixture: same pipe protocol, side effect only after bound approval."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

mode,workdir=sys.argv[2:4]
review='Exact fixture plan: create marker in '+workdir
if mode=='hang':
    sleeper=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
    Path(workdir,'pids').write_text(f'{os.getpid()} {sleeper.pid}')
    time.sleep(60)
else:
    digest=hashlib.sha256(review.encode()).hexdigest()
    print(json.dumps({'type':'approval_request','review':review,'sha256':digest if mode!='bad-hash' else '0'*64}),flush=True)
    response=json.loads(sys.stdin.readline())
    approved=response.get('decision')=='approve' and response.get('sha256')==digest
    if approved:Path(workdir,'marker').write_text('approved')
    print(json.dumps({'type':'result','result':{'approved':approved}}),flush=True)
