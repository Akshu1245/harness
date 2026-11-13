from rashi.council import debate


def mk(answers, votes):
    """Fake members: answers[name] is their answer, votes[name] the answer number they pick."""
    def one(name):
        def llm(system, user):
            if "voting on peer answers" in system:
                import json
                return json.dumps({"vote": votes[name], "why": "t"})
            return answers[name]
        return llm
    return {n: one(n) for n in answers}


def test_majority_wins():
    llms = mk({"a": "use sqlite", "b": "use postgres", "c": "use files"},
              {"a": 2, "b": 3, "c": 2})  # b cannot vote 2: that is its own answer
    r = debate(llms, "storage?")
    assert r["winner"] == "b" and r["tally"] == {2: 2, 3: 1}


def test_tie_goes_to_earliest_answer():
    llms = mk({"a": "x", "b": "y"}, {"a": 2, "b": 1})
    r = debate(llms, "q")
    assert r["tally"] == {1: 1, 2: 1} and r["winner"] == "a"


def test_sick_member_excluded_not_fatal():
    llms = mk({"a": "x", "b": "y"}, {"a": 2, "b": 1})
    def dead(system, user):
        raise ConnectionError("down")
    llms["dead"] = dead
    r = debate(llms, "q")
    assert "dead" in r["errors"] and "dead" not in r["answers"] and r["winner"] in ("a", "b")


def test_no_self_vote_and_abstain_recorded():
    # everyone votes for themselves -> all abstain, no winner
    llms = mk({"a": "x", "b": "y"}, {"a": 1, "b": 2})
    r = debate(llms, "q")
    assert r["votes"] == {} and r["winner"] is None
    assert any("abstained" in v for k, v in r["errors"].items())


def test_empty_answers_everywhere():
    llms = {"a": lambda s, u: "", "b": lambda s, u: "   "}
    r = debate(llms, "q")
    assert r["winner"] is None and set(r["errors"]) == {"a", "b"}
