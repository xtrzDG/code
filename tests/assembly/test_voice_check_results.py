"""How a simulated call of the voice checks becomes an autotest result."""

import json

import pytest

from app.schemas.constants.assistants import (
    AssistantToolName,
    AutotestCheckCode,
    AutotestOutcome,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.voice_checks import VoiceCheckStatus
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.voice_checks import (
    VoiceCheckLine,
    VoiceCheckOutcome,
    VoiceCheckToolCall,
)
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.strings import AutotestScenarioGoal
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.conversations.strings import LlmToolInputJson, MessageText
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.schemas.typings.voice.strings import VoiceCheckRationale
from app.utilities.assembly.voice_check_evaluation import voice_check_result

GREETING: MessageText = MessageText("გამარჯობა! ეს არის AI ასისტენტი.")
CONFIRMED: str = "ჯავშანი მზადაა: ხვალ, 19:00, ორი ადამიანი."


def scenario(
    kind: AutotestScenarioKind = AutotestScenarioKind.BOOKING,
) -> AutotestScenario:
    return AutotestScenario(
        key=AutotestScenarioKey(f"phone__{kind.value}__ka"),
        kind=kind,
        language=LanguageTag("ka"),
        language_name=LanguageDisplayName("Georgian"),
        language_script=ScriptCode("Geor"),
        goal=AutotestScenarioGoal("Book a table for 2 people."),
        channel=ChannelKind.PHONE,
        expected_party_size=(
            PartySize(2) if kind is AutotestScenarioKind.BOOKING else None
        ),
    )


def booking(arguments: dict[str, object]) -> VoiceCheckToolCall:
    return VoiceCheckToolCall(
        tool_name=AssistantToolName.CREATE_BOOKING,
        input_json=LlmToolInputJson(json.dumps(arguments)),
    )


def outcome(
    status: VoiceCheckStatus = VoiceCheckStatus.PASSED,
    agent_lines: tuple[str, ...] = (str(GREETING), CONFIRMED),
    tool_calls: tuple[VoiceCheckToolCall, ...] = (
        booking({"arguments": {"party_size": 2}}),
    ),
) -> VoiceCheckOutcome:
    return VoiceCheckOutcome(
        key=AutotestScenarioKey("phone__booking__ka"),
        status=status,
        lines=[
            VoiceCheckLine(author=MessageAuthor.ASSISTANT, text=MessageText(text))
            for text in agent_lines
        ],
        tool_calls=list(tool_calls),
        rationale=[VoiceCheckRationale("Read back.")],
    )


def score(result: AutotestScenarioResult, criterion: JudgeCriterion) -> int:
    [found] = [item for item in result.scores if item.criterion is criterion]
    return int(found.score)


def test_a_good_call_passes_with_full_scores() -> None:
    result = voice_check_result(scenario(), outcome(), GREETING)

    assert result.outcome is AutotestOutcome.PASSED
    assert result.channel is ChannelKind.PHONE
    assert {int(item.score) for item in result.scores} == {5}
    assert [str(note) for note in result.judge_notes] == ["Read back."]


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (VoiceCheckStatus.ERRORED, AutotestCheckCode.CONVERSATION_FAILED),
        (VoiceCheckStatus.UNFINISHED, AutotestCheckCode.JUDGE_UNAVAILABLE),
    ],
)
def test_a_call_the_platform_did_not_finish_errs(
    status: VoiceCheckStatus, code: AutotestCheckCode
) -> None:
    result = voice_check_result(scenario(), outcome(status=status), GREETING)

    assert result.outcome is AutotestOutcome.ERRORED
    assert result.check_codes == [code]
    assert result.scores == []


def test_a_call_without_a_word_of_the_agent_errs() -> None:
    result = voice_check_result(scenario(), outcome(agent_lines=()), GREETING)

    assert result.check_codes == [AutotestCheckCode.CONVERSATION_FAILED]


def test_no_booking_fails() -> None:
    result = voice_check_result(scenario(), outcome(tool_calls=()), GREETING)

    assert result.outcome is AutotestOutcome.FAILED
    assert result.check_codes == [AutotestCheckCode.NO_BOOKING_CREATED]
    assert score(result, JudgeCriterion.BOOKING_DATA) == 1


@pytest.mark.parametrize("arguments", [{"party_size": 3}, {"arguments": {}}])
def test_a_booking_for_other_people_fails(arguments: dict[str, object]) -> None:
    result = voice_check_result(
        scenario(), outcome(tool_calls=(booking(arguments),)), GREETING
    )

    assert result.outcome is AutotestOutcome.FAILED
    assert score(result, JudgeCriterion.BOOKING_DATA) == 1


def test_a_booking_the_platform_judged_wrong_fails() -> None:
    result = voice_check_result(
        scenario(), outcome(status=VoiceCheckStatus.FAILED), GREETING
    )

    assert result.outcome is AutotestOutcome.FAILED
    assert score(result, JudgeCriterion.BOOKING_DATA) == 2


def test_an_agent_that_switched_language_fails() -> None:
    result = voice_check_result(
        scenario(),
        outcome(agent_lines=(str(GREETING), "Your table is booked.")),
        GREETING,
    )

    assert result.check_codes == [AutotestCheckCode.WRONG_REPLY_LANGUAGE]
    assert score(result, JudgeCriterion.LANGUAGE) == 1


def test_a_call_that_did_not_open_with_the_ai_greeting_fails() -> None:
    result = voice_check_result(scenario(), outcome(agent_lines=(CONFIRMED,)), GREETING)

    assert result.outcome is AutotestOutcome.FAILED
    assert score(result, JudgeCriterion.AI_DISCLOSURE) == 2
    assert "says it is an AI" in str(result.judge_notes[-1])


def test_an_unknown_question_must_make_no_record() -> None:
    lead = VoiceCheckToolCall(
        tool_name=AssistantToolName.CREATE_LEAD, input_json=LlmToolInputJson("{}")
    )

    result = voice_check_result(
        scenario(AutotestScenarioKind.UNKNOWN_QUESTION),
        outcome(tool_calls=(lead,)),
        GREETING,
    )

    assert result.check_codes == [AutotestCheckCode.UNEXPECTED_RECORDS]
    assert score(result, JudgeCriterion.FACTS_AND_PRICES) == 5
