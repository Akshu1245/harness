"""Intake (his 2026-11-13 voice note): he refines an idea in another AI tool and pastes it
here. The harness asks every clarifying question ALL AT ONCE - one numbered batch,
multiple-choice where sensible - or he copies the batch into his own AI and pastes the
answers back. After that the build runs automated until the goal is reached or the loop
reports INCOMPLETE."""

QUESTIONS_SYS = (
    "You are the intake of a coding harness. Read the idea and ask every clarifying question "
    "that would materially change what gets built, ALL AT ONCE in one numbered batch. Give each "
    "question 2-4 multiple-choice options plus 'other'. No preamble, no summary, questions only.")


def questions(llm, idea):
    """One batch of clarifying questions for a pasted idea."""
    return llm(QUESTIONS_SYS, "IDEA:\n" + idea)


def with_answers(idea, answers):
    """The goal the build loop sees: the idea plus his answered intake batch."""
    answers = (answers or "").strip()
    return idea if not answers else idea + "\n\nANSWERS TO THE INTAKE QUESTIONS:\n" + answers
