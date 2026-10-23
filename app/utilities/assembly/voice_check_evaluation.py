"""
A simulated call of the voice checks as an autotest result (channel PHONE).

The voice platform's evaluator judges the call against its condition (the
booking, the disclosure, the language); the platform-independent checks
come on top: a booking scenario must call create_booking for the number of
people asked for, an unknown question none of the record tools, the call
must open with the greeting that says the agent is an AI, and the agent's
lines must be written in the scenario's script. Scores follow the judge's
scale (5 met, 2 or 1 not), so the run's average and its launch rules treat
voice checks like test chats.
"""

import json
from collections.abc import Sequence

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
from app.schemas.domain.assistants import (
    AutotestScenarioResult,
    AutotestTranscriptLine,
    JudgeCriterionScore,
)
from app.schemas.dto.assistants.autotest_runs import (
    AutotestCheckFailure,
    AutotestScenario,
)
from app.schemas.dto.voice_checks import VoiceCheckOutcome, VoiceCheckToolCall
from app.schemas.typings.assistants.constrained_integers import JudgeScore
from app.schemas.typings.assistants.strings import AutotestCheckNote, JudgeNote
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.assembly.autotest_evaluation import check_failure, decide_outcome
from app.utilities.assembly.script_detection import is_written_in_script

MET: JudgeScore = JudgeScore(5)
PARTLY_MISSED: JudgeScore = JudgeScore(2)
MISSED: JudgeScore = JudgeScore(1)
RECORD_TOOLS: frozenset[AssistantToolName] = frozenset(
    {AssistantToolName.CREATE_BOOKING, AssistantToolName.CREATE_LEAD}
)
NOT_PLAYED: dict[VoiceCheckStatus, tuple[AutotestCheckCode, str]] = {
    VoiceCheckStatus.ERRORED: (
        AutotestCheckCode.CONVERSATION_FAILED,
        "The voice platform could not play the simulated call.",
    ),
    VoiceCheckStatus.UNFINISHED: (
        AutotestCheckCode.JUDGE_UNAVAILABLE,
        "The simulated call did not finish in time.",
    ),
}


def voice_check_result(
    scenario: AutotestScenario,
    outcome: VoiceCheckOutcome,
    greeting: MessageText | None,
) -> AutotestScenarioResult:
    """The result of one simulated call; `greeting` opens a call in its language."""

    transcript: list[AutotestTranscriptLine] = [
        AutotestTranscriptLine(author=line.author, text=line.text)
        for line in outcome.lines
    ]
    agent_lines: list[str] = [
        str(line.text)
        for line in outcome.lines
        if line.author is MessageAuthor.ASSISTANT
    ]
    not_played: tuple[AutotestCheckCode, str] | None = NOT_PLAYED.get(outcome.status)
    if not_played is not None or not agent_lines:
        code, note = not_played or NOT_PLAYED[VoiceCheckStatus.ERRORED]
        return not_played_result(scenario, outcome, transcript, code, note)

    failures: list[AutotestCheckFailure] = check_tools(scenario, outcome.tool_calls)
    is_greeted: bool = opens_with(agent_lines[0], greeting)
    # The greeting is the platform's text, not the model's speech.
    spoken_lines: list[str] = agent_lines[1:] if is_greeted else agent_lines
    if any(
        is_written_in_script(text, scenario.language_script) is False
        for text in spoken_lines
    ):
        failures.append(
            check_failure(
                AutotestCheckCode.WRONG_REPLY_LANGUAGE,
                f"The agent did not speak {scenario.language_name} throughout.",
            )
        )

    is_platform_passed: bool = outcome.status is VoiceCheckStatus.PASSED
    task_score: JudgeScore = task_score_of(scenario, outcome, is_platform_passed)
    disclosure_score: JudgeScore = MET if is_greeted else PARTLY_MISSED
    scores: list[JudgeCriterionScore] = [
        JudgeCriterionScore(criterion=task_criterion(scenario), score=task_score),
        JudgeCriterionScore(
            criterion=JudgeCriterion.AI_DISCLOSURE, score=disclosure_score
        ),
        JudgeCriterionScore(
            criterion=JudgeCriterion.LANGUAGE,
            score=MET
            if not any(
                f.code is AutotestCheckCode.WRONG_REPLY_LANGUAGE for f in failures
            )
            else MISSED,
        ),
    ]
    judge_notes: list[JudgeNote] = [JudgeNote(str(text)) for text in outcome.rationale]
    if disclosure_score is not MET:
        judge_notes.append(
            JudgeNote("The call did not open with the greeting that says it is an AI.")
        )

    check_notes: list[AutotestCheckNote] = [failure.note for failure in failures]
    return AutotestScenarioResult(
        scenario_key=scenario.key,
        kind=scenario.kind,
        language=scenario.language,
        outcome=decide_outcome(scores, check_notes),
        scores=scores,
        judge_notes=judge_notes,
        check_notes=check_notes,
        check_codes=[failure.code for failure in failures],
        transcript=transcript,
        cost_micro_usd=outcome.cost_micro_usd,
        channel=ChannelKind.PHONE,
    )


def check_tools(
    scenario: AutotestScenario, tool_calls: Sequence[VoiceCheckToolCall]
) -> list[AutotestCheckFailure]:
    """A booking must be made, an unknown question must make no record."""

    called: list[AssistantToolName] = [call.tool_name for call in tool_calls]
    if scenario.kind is AutotestScenarioKind.BOOKING:
        if AssistantToolName.CREATE_BOOKING not in called:
            return [
                check_failure(
                    AutotestCheckCode.NO_BOOKING_CREATED, "No booking was made."
                )
            ]

        return []

    made: int = sum(1 for tool_name in called if tool_name in RECORD_TOOLS)
    if made:
        return [
            check_failure(
                AutotestCheckCode.UNEXPECTED_RECORDS,
                f"Made {made} booking(s) or request(s) although none was expected.",
            )
        ]

    return []


def task_score_of(
    scenario: AutotestScenario,
    outcome: VoiceCheckOutcome,
    is_platform_passed: bool,
) -> JudgeScore:
    """
    The booking's (or the answer's) score: met when the platform passed the
    call and, for a booking, it was made for the people asked for.
    """

    if scenario.kind is AutotestScenarioKind.BOOKING:
        party_sizes: list[int | None] = [
            read_party_size(call)
            for call in outcome.tool_calls
            if call.tool_name is AssistantToolName.CREATE_BOOKING
        ]
        if not party_sizes or (
            scenario.expected_party_size is not None
            and int(scenario.expected_party_size) not in party_sizes
        ):
            return MISSED

    return MET if is_platform_passed else PARTLY_MISSED


def task_criterion(scenario: AutotestScenario) -> JudgeCriterion:
    if scenario.kind is AutotestScenarioKind.BOOKING:
        return JudgeCriterion.BOOKING_DATA

    return JudgeCriterion.FACTS_AND_PRICES


def read_party_size(call: VoiceCheckToolCall) -> int | None:
    """`party_size` of a tool call, at the top or under "arguments"."""

    try:
        parsed: object = json.loads(str(call.input_json))
    except ValueError:
        return None

    if not isinstance(parsed, dict):
        return None

    arguments: object = parsed.get("arguments", parsed)
    value: object = arguments.get("party_size") if isinstance(arguments, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def opens_with(first_line: str, greeting: MessageText | None) -> bool:
    """The agent's first line is its greeting (spaces aside)."""

    if greeting is None:
        return False

    return " ".join(first_line.split()) == " ".join(str(greeting).split())


def not_played_result(
    scenario: AutotestScenario,
    outcome: VoiceCheckOutcome,
    transcript: list[AutotestTranscriptLine],
    code: AutotestCheckCode,
    note: str,
) -> AutotestScenarioResult:
    return AutotestScenarioResult(
        scenario_key=scenario.key,
        kind=scenario.kind,
        language=scenario.language,
        outcome=AutotestOutcome.ERRORED,
        check_notes=[AutotestCheckNote(note)],
        check_codes=[code],
        transcript=transcript,
        cost_micro_usd=outcome.cost_micro_usd,
        channel=ChannelKind.PHONE,
    )
