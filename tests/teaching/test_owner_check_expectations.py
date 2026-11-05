"""Whether the assistant's answers met an owner check: a deterministic check."""

import pytest

from app.schemas.constants.assistants import AutotestCheckCode, AutotestExpectation
from app.schemas.dto.assistants.autotest_runs import OwnerCheckSpec
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.owner_check_evaluation import (
    check_owner_expectation,
    mentions,
)


def spec(
    expectation: AutotestExpectation, expected_text: str | None = None
) -> OwnerCheckSpec:
    return OwnerCheckSpec(
        case_id=AutotestCaseId(),
        question=AutotestCaseQuestion("Можно со своим тортом?"),
        expectation=expectation,
        expected_text=None
        if expected_text is None
        else AutotestExpectedText(expected_text),
    )


def reply(
    text: str | None,
    *,
    disclosure: str | None = None,
    handed_off: bool = False,
    lead: bool = False,
) -> AssistantReply:
    return AssistantReply(
        conversation_id=ConversationId(),
        text=None if text is None else MessageText(text),
        language=LanguageTag("ru"),
        disclosure_text=None if disclosure is None else MessageText(disclosure),
        is_handed_off=handed_off,
        created_handoff_ids=[HandoffId()] if handed_off else [],
        created_lead_ids=[LeadId()] if lead else [],
    )


@pytest.mark.parametrize(
    ("text", "expected", "found"),
    [
        ("Да, со СВОИМ тортом можно!", "своим тортом", True),
        ("We have vegetarians' dishes", "vegetarian", True),
        ("Есть вегетарианское меню", "вегетарианск", True),
        ("Café opens at nine", "cafe", True),
        ("Tortoise soup", "tort", True),
        ("Без десерта", "торт", False),
        ("Натюрморт", "торт", False),
        ("anything", "?!", False),
    ],
)
def test_the_expected_words_start_a_word_of_the_answer(
    text: str, expected: str, found: bool
) -> None:
    assert mentions(text, expected) is found


def test_must_mention_passes_when_any_answer_names_the_text() -> None:
    check = spec(AutotestExpectation.MUST_MENTION, "своим тортом")

    assert (
        check_owner_expectation(
            check, [reply("Минутку."), reply("Да, со своим тортом можно.")]
        )
        == []
    )
    failures = check_owner_expectation(check, [reply("Нет."), reply(None)])
    assert [failure.code for failure in failures] == [
        AutotestCheckCode.EXPECTED_TEXT_MISSING
    ]
    assert "своим тортом" in str(failures[0].note)


def test_the_disclosure_in_front_of_a_reply_is_not_the_answer() -> None:
    check = spec(AutotestExpectation.MUST_MENTION, "AI")
    disclosed = reply("Я AI-ассистент.\nНет.", disclosure="Я AI-ассистент.")

    assert [
        failure.code for failure in check_owner_expectation(check, [disclosed])
    ] == [AutotestCheckCode.EXPECTED_TEXT_MISSING]


def test_must_not_mention_fails_when_an_answer_names_the_text() -> None:
    check = spec(AutotestExpectation.MUST_NOT_MENTION, "скидк")

    assert check_owner_expectation(check, [reply("Цены как в меню.")]) == []
    assert [
        failure.code
        for failure in check_owner_expectation(check, [reply("Дадим скидку 10%.")])
    ] == [AutotestCheckCode.FORBIDDEN_TEXT_MENTIONED]


def test_must_hand_off_needs_a_handoff() -> None:
    check = spec(AutotestExpectation.MUST_HAND_OFF)

    assert check_owner_expectation(check, [reply(None, handed_off=True)]) == []
    assert [
        failure.code for failure in check_owner_expectation(check, [reply("Сам.")])
    ] == [AutotestCheckCode.NOT_HANDED_OFF]


def test_must_create_lead_needs_a_request() -> None:
    check = spec(AutotestExpectation.MUST_CREATE_LEAD)

    assert check_owner_expectation(check, [reply("Записал.", lead=True)]) == []
    assert [
        failure.code for failure in check_owner_expectation(check, [reply("Ок.")])
    ] == [AutotestCheckCode.NO_LEAD_CREATED]
