"""Council: multi-model debate + vote (R9, rebuilt inside the package - the old root scripts
polled 3-4 gateways once and dumped JSON; this is the reusable, testable form).

Flow per question: every member answers independently (fresh context each), then every member
sees the anonymized peer answers and votes for the best one that is not its own. Votes are
counted deterministically; ties resolve to the earliest answer. Advisory only: a council
verdict is a recommendation, never an auto-executed decision, and NEVER_LIE applies to prompts.

`llms` is {name: callable(system, user) -> str}: tests run with fakes, no network, no spend.
A member that raises or answers empty is recorded and excluded from the vote, not retried forever.
"""
import json
import re

from .rules import NEVER_LIE

ANSWER_SYS = "Answer concretely and specifically. " + NEVER_LIE
VOTE_SYS = ("You are voting on peer answers to a question. Reply with JSON only: "
            "{\"vote\": <answer number>, \"why\": str}. You may not vote for your own answer.")


def debate(llms, question, max_answer_chars=4000):
    """Round 1: independent answers. Round 2: each member votes on anonymized peers.
    Returns {question, answers, votes, tally, winner, errors}. Deterministic tally."""
    answers, errors = {}, {}
    for name, llm in llms.items():
        try:
            text = llm(ANSWER_SYS, question) or ""
        except Exception as ex:  # a sick gateway must not kill the council
            errors[name] = f"{type(ex).__name__}: {str(ex)[:120]}"
            continue
        if text.strip():
            answers[name] = text[:max_answer_chars]
        else:
            errors[name] = "empty answer"
    if not answers:
        return {"question": question, "answers": {}, "votes": {}, "tally": {}, "winner": None,
                "errors": errors}
    names = list(answers)
    ballot = "\n\n".join(f"ANSWER {i + 1}:\n{answers[n]}" for i, n in enumerate(names))
    votes = {}
    for name, llm in llms.items():
        if name not in answers:
            continue
        own = names.index(name) + 1
        user = (f"QUESTION:\n{question}\n\n{ballot}\n\nYour own answer was ANSWER {own}; "
                "vote for a different one.")
        vote = None
        for attempt in range(2):
            try:
                raw = llm(VOTE_SYS, user if attempt == 0 else "JSON only.\n\n" + user) or ""
            except Exception as ex:
                errors[name + " (vote)"] = f"{type(ex).__name__}: {str(ex)[:120]}"
                break
            m = re.search(r"\{.*\}", raw, re.S)
            try:
                vote = json.loads(m.group(0)).get("vote") if m else None
            except ValueError:
                vote = None
            if isinstance(vote, int) and 1 <= vote <= len(names) and vote != own:
                break
            vote = None
        if vote is not None:
            votes[name] = vote
        else:
            errors.setdefault(name + " (vote)", "abstained: no valid vote")
    tally = {}
    for v in votes.values():
        tally[v] = tally.get(v, 0) + 1
    winner = None
    if tally:
        top = max(tally.values())
        winner = names[min(v for v, c in tally.items() if c == top) - 1]  # earliest answer on a tie
    return {"question": question, "answers": answers, "votes": votes, "tally": tally,
            "winner": winner, "errors": errors}
