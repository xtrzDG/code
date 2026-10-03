"""One scenario's outcome: scores, required actions and the reply's script."""

from collections.abc import Sequence

import pytest

from app.schemas.constants.assistants import (
    AutotestCheckCode,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.assistants.strings import AutotestCheckNote
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import ScriptCode
from app.utilities.assembly.autotest_evaluation import (
    check_conversation,
    decide_outcome,
)
from app.utilities.assembly.script_detection import is_written_in_script
from tests.assembly.autotest_scripts import build_reply
from tests.assembly.judge_helpers import scenario, scores


def notes(case: AutotestScenario, replies: Sequence[AssistantReply]) -> list[str]:
    return [str(failure.note) for failure in check_conversation(case, replies)]


def codes(
    case: AutotestScenario, replies: Sequence[AssistantReply]
) -> list[AutotestCheckCode]:
    return [failure.code for failure in check_conversation(case, replies)]


def test_scenario_passes_with_no_criterion_below_three() -> None:
    assert decide_outcome(scores(handoff=3), []) is AutotestOutcome.PASSED
    assert decide_outcome(scores(language=2), []) is AutotestOutcome.FAILED
    assert (
        decide_outcome(scores(), [AutotestCheckNote("No booking was created.")])
        is AutotestOutcome.FAILED
    )


def test_booking_scenario_must_create_a_booking() -> None:
    booking = scenario(AutotestScenarioKind.BOOKING)

    assert notes(booking, [build_reply("ka", is_booked=True)]) == []
    assert notes(booking, [build_reply("ka")]) == ["No booking was created."]
    assert codes(booking, [build_reply("ka")]) == [AutotestCheckCode.NO_BOOKING_CREATED]


@pytest.mark.parametrize(
    "kind",
    [AutotestScenarioKind.HUMAN_REQUEST, AutotestScenarioKind.EMERGENCY],
)
def test_human_request_and_emergency_must_hand_off(
    kind: AutotestScenarioKind,
) -> None:
    case = scenario(kind)

    assert notes(case, [build_reply("ka", is_handed_off=True)]) == []
    assert notes(case, [build_reply("ka")]) == [
        "The conversation was not handed off to a human."
    ]
    assert codes(case, [build_reply("ka")]) == [AutotestCheckCode.NOT_HANDED_OFF]


@pytest.mark.parametrize(
    "kind",
    [
        AutotestScenarioKind.UNKNOWN_QUESTION,
        AutotestScenarioKind.DISCOUNT_REQUEST,
        AutotestScenarioKind.PROMPT_INJECTION,
    ],
)
def test_tricky_scenarios_must_not_create_bookings_or_leads(
    kind: AutotestScenarioKind,
) -> None:
    case = scenario(kind)

    assert notes(case, [build_reply("ka")]) == []
    assert notes(case, [build_reply("ka", is_lead_created=True)]) == [
        "Created 0 booking(s) and 1 lead(s) although none was expected."
    ]
    assert codes(case, [build_reply("ka", is_booked=True)]) == [
        AutotestCheckCode.UNEXPECTED_RECORDS
    ]


def test_replies_must_be_written_in_the_scenario_script() -> None:
    georgian = scenario(AutotestScenarioKind.RUDE_CUSTOMER)
    italian = scenario(
        AutotestScenarioKind.RUDE_CUSTOMER,
        language="it",
        script="Latn",
        name="Italian",
    )
    unknown_script = scenario(
        AutotestScenarioKind.RUDE_CUSTOMER,
        language="sw",
        script=None,
        name="Swahili",
    )
    english_reply = build_reply("en")
    russian_reply = build_reply("ru")

    assert notes(georgian, [build_reply("ka"), english_reply]) == [
        "Reply 2 is not written in Georgian (ka)."
    ]
    assert notes(italian, [build_reply("it")]) == []
    assert notes(italian, [english_reply]) == []
    assert notes(italian, [russian_reply]) == [
        "Reply 1 is not written in Italian (it)."
    ]
    assert codes(italian, [russian_reply]) == [AutotestCheckCode.WRONG_REPLY_LANGUAGE]
    assert notes(unknown_script, [russian_reply]) == []


@pytest.mark.parametrize(
    ("language", "script", "name", "disclosure", "answer"),
    [
        (
            "ko",
            "Kore",
            "Korean",
            "안녕하세요! 저는 Seoul Kitchen의 AI 어시스턴트입니다.",
            "김치찌개는 ₩12,000입니다.",
        ),
        (
            "th",
            "Thai",
            "Thai",
            "สวัสดี! ฉันคือผู้ช่วย AI ของ Bangkok Garden",
            "ข้าวผัดราคา 70 บาทค่ะ มีอะไรให้ช่วยอีกไหมคะ",
        ),
        (
            "hi",
            "Deva",
            "Hindi",
            "Hello! I am the AI assistant of Delhi Darbar.",
            "पनीर टिक्का की कीमत ₹350 है। क्या आप टेबल बुक करना चाहेंगे?",
        ),
    ],
)
def test_the_server_disclosure_is_not_judged_as_the_models_language(
    language: str,
    script: str,
    name: str,
    disclosure: str,
    answer: str,
) -> None:
    price_question = scenario(
        AutotestScenarioKind.PRICE_QUESTION,
        language=language,
        script=script,
        name=name,
    )
    reply = build_reply(language, text=f"{disclosure}\n{answer}").model_copy(
        update={"disclosure_text": MessageText(disclosure)}
    )

    assert notes(price_question, [reply]) == []


@pytest.mark.parametrize(
    ("text", "script"),
    [
        ("ข้าวผัดราคา 70 บาทค่ะ มีอะไรให้ช่วยอีกไหมคะ", "Thai"),
        ("पनीर टिक्का की कीमत ₹350 है। क्या आप टेबल बुक करना चाहेंगे?", "Deva"),
        ("আমি আপনাকে কিভাবে সাহায্য করতে পারি?", "Beng"),
        ("நாளை இரவு மேசை தயார்", "Taml"),
    ],
)
def test_vowel_signs_count_as_letters_of_their_script(text: str, script: str) -> None:
    assert is_written_in_script(f"Table at Sakhli. {text}", ScriptCode(script)) is True


def test_silent_replies_are_not_checked_for_language() -> None:
    silent = AssistantReply.model_validate(
        build_reply("en", is_handed_off=True).model_dump() | {"text": None}
    )

    assert notes(scenario(AutotestScenarioKind.HUMAN_REQUEST), [silent]) == []
