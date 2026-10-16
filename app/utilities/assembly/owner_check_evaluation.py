"""
Whether the assistant's answers met an owner check's expectation: a
deterministic check, no judge.

Texts are compared as folded words (case, accents, punctuation and
spacing ignored, `search_text.fold_words`); the expected text matches
where its words start a word of the answer, so "vegetarian" also matches
"vegetarians" and "вегетарианск" matches "вегетарианское". The AI
disclosure the server puts in front of the first reply is not the model's
writing and is left out.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestCheckCode, AutotestExpectation
from app.schemas.dto.assistants.autotest_runs import (
    AutotestCheckFailure,
    OwnerCheckSpec,
)
from app.schemas.dto.conversations import AssistantReply
from app.utilities.assembly.autotest_evaluation import check_failure, read_model_text
from app.utilities.knowledge.search_text import fold_words


def mentions(text: str, expected: str) -> bool:
    """Whether the folded words of `expected` start at a word of `text`."""

    folded_expected: str = fold_words(expected)
    if folded_expected == "":
        return False

    return f" {folded_expected}" in f" {fold_words(text)}"


def check_owner_expectation(
    check: OwnerCheckSpec,
    replies: Sequence[AssistantReply],
) -> list[AutotestCheckFailure]:
    """
    MUST_MENTION: some answer names the expected text; MUST_NOT_MENTION: no
    answer names it; MUST_HAND_OFF: the conversation went to a person;
    MUST_CREATE_LEAD: a request (lead) was created. Each failure is a code
    with an English note.
    """

    answers: list[str] = [read_model_text(reply) for reply in replies]
    expected: str = "" if check.expected_text is None else str(check.expected_text)
    if check.expectation is AutotestExpectation.MUST_MENTION:
        if any(mentions(answer, expected) for answer in answers):
            return []

        return [
            check_failure(
                AutotestCheckCode.EXPECTED_TEXT_MISSING,
                f'No answer mentioned "{expected}".',
            )
        ]

    if check.expectation is AutotestExpectation.MUST_NOT_MENTION:
        if not any(mentions(answer, expected) for answer in answers):
            return []

        return [
            check_failure(
                AutotestCheckCode.FORBIDDEN_TEXT_MENTIONED,
                f'An answer mentioned "{expected}", which it must not.',
            )
        ]

    if check.expectation is AutotestExpectation.MUST_HAND_OFF:
        if any(reply.is_handed_off or reply.created_handoff_ids for reply in replies):
            return []

        return [
            check_failure(
                AutotestCheckCode.NOT_HANDED_OFF,
                "The conversation was not handed off to a human.",
            )
        ]

    if any(reply.created_lead_ids for reply in replies):
        return []

    return [check_failure(AutotestCheckCode.NO_LEAD_CREATED, "No request was created.")]
