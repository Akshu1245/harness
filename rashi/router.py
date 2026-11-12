"""Router: Laya first, rules as fallback, every decision logged, calibration on our own data.
`laya` is an optional callable laya(task, roles) -> {role: prob}. If absent or it raises, rules decide.
Laya is NOT tested in this repo's CI (needs model weights); the adapter is unverified until run."""
import json, time
from collections import Counter
from pathlib import Path
from .roles import ROLES, KEYWORDS


def rule_route(task):
    t = task.lower()
    for role in ("bounty-scout", "security", "reviewer", "planner", "coder"):
        if any(k in t for k in KEYWORDS[role]):
            return role
    return "coder"


def route(task, laya=None, threshold=0.7, log_path=None):
    roles = list(ROLES)
    rec = {"ts": time.time(), "task": task, "decider": "rules", "probs": None, "laya_error": None}
    chosen = None
    if laya is not None:
        try:
            probs = laya(task, roles)
            top = max(probs, key=probs.get)
            rec["probs"] = {k: round(v, 4) for k, v in probs.items()}
            if top in ROLES and probs[top] >= threshold:
                chosen, rec["decider"] = top, "laya"
        except Exception as ex:
            rec["laya_error"] = f"{type(ex).__name__}: {str(ex)[:120]}"
    if chosen is None:
        chosen = rule_route(task)
    rec["role"] = chosen
    rec["rules_role"] = rule_route(task)
    if log_path:
        with open(log_path, "a") as f:
            f.write(json.dumps(rec) + "\n")
    return chosen, rec


def calibrate(log_path, truth):
    """truth: {task: correct_role} from our own labelled outcomes. Returns real numbers, no spin."""
    rows = [json.loads(l) for l in Path(log_path).read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r["task"] in truth]
    if not rows:
        return {"n": 0}
    n = len(rows)
    acc = lambda pick: sum(pick(r) == truth[r["task"]] for r in rows) / n
    lay = [r for r in rows if r["probs"]]
    laya_top = (lambda r: max(r["probs"], key=r["probs"].get))
    maj = Counter(truth[r["task"]] for r in rows).most_common(1)[0][0]
    out = {"n": n, "rules_acc": acc(lambda r: r["rules_role"]), "majority_acc": acc(lambda r: maj),
           "used_acc": acc(lambda r: r["role"]), "laya_rows": len(lay)}
    if lay:
        out["laya_acc"] = sum(laya_top(r) == truth[r["task"]] for r in lay) / len(lay)
        out["rules_acc_same_rows"] = sum(r["rules_role"] == truth[r["task"]] for r in lay) / len(lay)
        out["laya_beats_rules"] = out["laya_acc"] > out["rules_acc_same_rows"]
    return out
