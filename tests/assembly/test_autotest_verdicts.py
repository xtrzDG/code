"""Autotest verdicts: failed, low-scored, unreadable and errored scenarios."""

import pytest

from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
)
from tests.assembly.autotest_run_helpers import (
    GEORGIAN_SCENARIO_COUNT,
    results_by_key,
    start,
)
from tests.assembly.autotest_scripts import build_reply
from tests.assembly.testbed import AssemblyTestbed


def test_one_failed_price_scenario_blocks_ready() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_scores["price_question__ru__2"] = {
        "facts_and_prices": 2,
        "booking_data": 5,
        "ai_disclosure": 5,
        "handoff": 5,
        "language": 5,
    }

    run = testbed.run_autotests(business.id, version.id)

    results = results_by_key(run)
    assert results["price_question__ru__2"].outcome is AutotestOutcome.FAILED
    assert run.passed_count == GEORGIAN_SCENARIO_COUNT - 1
    assert run.average_score is not None
    assert float(run.average_score) > 4.0
    assert run.is_passed is False
    assert run.version_status is AssistantVersionStatus.TESTS_FAILED
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.TESTS_FAILED
    )


def test_average_below_four_blocks_ready_even_if_every_scenario_passed() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    low_but_passing = {
        "facts_and_prices": 4,
        "booking_data": 4,
        "ai_disclosure": 4,
        "handoff": 3,
        "language": 4,
    }
    for language in ("ka", "ru", "en"):
        for kind in AutotestScenarioKind:
            testbed.judge_scores[f"{kind.value}__{language}"] = low_but_passing

    testbed.judge_scores["price_question__ka__1"] = low_but_passing
    testbed.judge_scores["price_question__ru__2"] = low_but_passing

    run = testbed.run_autotests(business.id, version.id)

    assert run.passed_count == GEORGIAN_SCENARIO_COUNT
    assert run.average_score is not None
    assert float(run.average_score) == pytest.approx(3.8)
    assert run.is_passed is False
    assert run.version_status is AssistantVersionStatus.TESTS_FAILED
    assert testbed.version(business.id, version.id).test_score == run.average_score


def test_unreadable_judge_answer_errors_only_that_scenario() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_raw_answers["rude_customer__en"] = "The assistant was great!"

    run = testbed.run_autotests(business.id, version.id)

    result = results_by_key(run)["rude_customer__en"]
    assert result.outcome is AutotestOutcome.ERRORED
    assert result.check_notes == ["The judge's answer could not be read."]
    assert result.scores == []
    assert run.is_passed is True
    assert run.version_status is AssistantVersionStatus.READY


def test_unreadable_judge_answer_on_a_booking_scenario_blocks_ready() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_raw_answers["booking__ka"] = '{"scores": {"facts_and_prices": 9}}'

    run = testbed.run_autotests(business.id, version.id)

    assert results_by_key(run)["booking__ka"].outcome is AutotestOutcome.ERRORED
    assert run.version_status is AssistantVersionStatus.TESTS_FAILED


def test_provider_errors_error_the_scenario_but_not_the_run() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_errors.add("discount_request__ka")

    def failing_reply(
        message: InboundMessage,
        scenario_key: str,
        turn_index: int,
    ) -> AssistantReply:
        raise ExternalServiceError("Language model is unavailable.")

    testbed.reply_scripts["unknown_question__ru"] = failing_reply

    run = testbed.run_autotests(business.id, version.id)

    results = results_by_key(run)
    judge_failure = results["discount_request__ka"]
    engine_failure = results["unknown_question__ru"]
    assert judge_failure.outcome is AutotestOutcome.ERRORED
    assert judge_failure.check_notes == [
        "The judge could not be asked: Judge model is unavailable."
    ]
    assert len(judge_failure.transcript) == 2
    assert engine_failure.outcome is AutotestOutcome.ERRORED
    assert engine_failure.check_notes == [
        "The test conversation could not run: Language model is unavailable."
    ]
    assert [line.author for line in engine_failure.transcript] == [
        MessageAuthor.CUSTOMER
    ]
    assert run.scenario_count == GEORGIAN_SCENARIO_COUNT


@pytest.mark.parametrize(
    ("scenario_key", "reply", "note"),
    [
        ("booking__en", build_reply("en"), "No booking was created."),
        (
            "human_request__ka",
            build_reply("ka"),
            "The conversation was not handed off to a human.",
        ),
        (
            "discount_request__ru",
            build_reply("ru", is_lead_created=True),
            "Created 0 booking(s) and 1 lead(s) although none was expected.",
        ),
        (
            "unknown_question__ka",
            build_reply("en"),
            "Reply 1 is not written in Georgian (ka).",
        ),
    ],
)
def test_deterministic_checks_fail_scenarios_the_judge_liked(
    scenario_key: str,
    reply: AssistantReply,
    note: str,
) -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.reply_scripts[scenario_key] = lambda message, key, turn: reply

    run = testbed.run_autotests(business.id, version.id)

    result = results_by_key(run)[scenario_key]
    assert result.outcome is AutotestOutcome.FAILED
    assert result.check_notes == [note]
    assert [int(score.score) for score in result.scores] == [5, 5, 5, 5, 5]
