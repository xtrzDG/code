"""
Voice checks gate going live whatever their kind: a version without
bookings is checked with an unknown-question call, and that call failing
(an invented answer, a record made) or erring (the voice platform down)
keeps the version from customers just like a failed booking call.
"""

from app.schemas.constants.assistants import (
    AssistantToolName,
    AutotestOutcome,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.domain.assistants import AutotestScenarioResult, JudgeCriterionScore
from app.schemas.dto.voice_checks import VoiceCheckToolCall
from app.schemas.typings.assistants.constrained_integers import JudgeScore
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.conversations.strings import LlmToolInputJson
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.autotests.voice_checks.run_voice_checks_use_case import (
    errored_result,
)
from app.utilities.assembly.autotest_evaluation import summarize_run
from app.utilities.assembly.voice_check_evaluation import voice_check_result
from tests.assembly.test_voice_check_results import GREETING, outcome, scenario

UNKNOWN_QUESTION = AutotestScenarioKind.UNKNOWN_QUESTION


def chat_pass(kind: AutotestScenarioKind) -> AutotestScenarioResult:
    return AutotestScenarioResult(
        scenario_key=AutotestScenarioKey(f"{kind.value}__ka"),
        kind=kind,
        language=LanguageTag("ka"),
        outcome=AutotestOutcome.PASSED,
        scores=[
            JudgeCriterionScore(criterion=criterion, score=JudgeScore(5))
            for criterion in JudgeCriterion
        ],
    )


CHAT_RUN: list[AutotestScenarioResult] = [
    chat_pass(AutotestScenarioKind.PRICE_QUESTION),
    chat_pass(UNKNOWN_QUESTION),
]


def test_a_failed_unknown_question_call_blocks_the_launch() -> None:
    lead = VoiceCheckToolCall(
        tool_name=AssistantToolName.CREATE_LEAD, input_json=LlmToolInputJson("{}")
    )
    failed = voice_check_result(
        scenario(UNKNOWN_QUESTION), outcome(tool_calls=(lead,)), GREETING
    )
    assert failed.outcome is AutotestOutcome.FAILED

    assert summarize_run(CHAT_RUN).is_passed
    assert not summarize_run([*CHAT_RUN, failed]).is_passed


def test_an_errored_unknown_question_call_blocks_the_launch() -> None:
    errored = errored_result(scenario(UNKNOWN_QUESTION), "The voice platform is down.")

    assert not summarize_run([*CHAT_RUN, errored]).is_passed


def test_a_passed_unknown_question_call_lets_it_go_live() -> None:
    passed = voice_check_result(
        scenario(UNKNOWN_QUESTION), outcome(tool_calls=()), GREETING
    )
    assert passed.outcome is AutotestOutcome.PASSED

    assert summarize_run([*CHAT_RUN, passed]).is_passed


def test_a_failed_chat_unknown_question_still_does_not_block_alone() -> None:
    failed_chat = chat_pass(UNKNOWN_QUESTION).model_copy(
        update={"outcome": AutotestOutcome.FAILED}
    )

    assert summarize_run([*CHAT_RUN, failed_chat]).is_passed
