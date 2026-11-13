from rashi import intake


def test_questions_are_one_batch_from_the_idea():
    seen = {}

    def llm(system, user):
        seen["user"] = user
        return "1. Which language? a) Python b) JS c) other"
    q = intake.questions(llm, "a todo cli")
    assert "1." in q and "a todo cli" in seen["user"]


def test_with_answers_folds_them_into_the_goal():
    assert intake.with_answers("idea", "") == "idea"
    out = intake.with_answers("idea", "1. a")
    assert out.startswith("idea") and "ANSWERS TO THE INTAKE QUESTIONS" in out and "1. a" in out
