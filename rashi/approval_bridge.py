"""One build process, one generated plan, one exact digest-bound approval.
The DSH host owns the human decision; the model cannot provide an approval flag in tool args.
This pipe protocol is for trusted local adapters, not a sandbox against hostile host processes.
"""
import hashlib
import json
import sys


def approval_text(spec,findings):
    return spec + '\n\nReview findings:\n' + json.dumps(findings,indent=2)


def request(spec,findings,read,write):
    review=approval_text(spec,findings)
    digest=hashlib.sha256(review.encode()).hexdigest()
    write.write(json.dumps({'type':'approval_request','review':review,'sha256':digest})+'\n')
    write.flush()
    line=read.readline(262144)
    try:
        response=json.loads(line)
    except (ValueError,TypeError):
        return False
    return (isinstance(response,dict) and response.get('decision')=='approve' and
            response.get('sha256')==digest)


def main(goal,workdir,read=None,write=None):
    from .__main__ import find_llm,make_llm
    from .build import one_press
    read,write=read or sys.stdin,write or sys.stdout
    found=find_llm()
    if not found:
        result={'status':'NO_FREE_MODEL_CONFIGURED'}
    else:
        result=one_press(goal,workdir,make_llm(*found),
                         lambda spec,findings:request(spec,findings,read,write))
    write.write(json.dumps({'type':'result','result':result})+'\n');write.flush()
    return 0
