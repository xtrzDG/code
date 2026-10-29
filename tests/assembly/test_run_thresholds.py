"""Run thresholds: critical scenarios and the average score decide the launch."""

import pytest

from app.schemas.constants.assistants import AutotestOutcome, AutotestScenarioKind
from app.utilities.assembly.autotest_evaluation import summarize_run
from tests.assembly.judge_helpers import result, scores


def test_run_passes_with_all_critical_scenarios_and_average_four() -> None:
    summary = summarize_run(
        [
            result(AutotestScenarioKind.BOOKING, AutotestOutcome.PASSED, scores()),
            result(
                AutotestScenarioKind.PRICE_QUESTION,
                AutotestOutcome.PASSED,
                scores(handoff=3, language=3, booking_data=3),
            ),
            result(
                AutotestScenarioKind.RUDE_CUSTOMER,
                AutotestOutcome.FAILED,
                scores(ai_disclosure=2, facts_and_prices=3),
            ),
        ]
    )

    assert summary.is_passed is True
    assert summary.scenario_count == 3
    assert summary.passed_count == 2
    assert summary.pass_rate == pytest.approx(2 / 3)
    assert summary.average_score is not None
    assert float(summary.average_score) == pytest.approx(64 / 15)


def test_one_failed_price_scenario_blocks_the_launch() -> None:
    summary = summarize_run(
        [
            result(AutotestScenarioKind.BOOKING, AutotestOutcome.PASSED),
            result(AutotestScenarioKind.PRICE_QUESTION, AutotestOutcome.PASSED),
            result(
                AutotestScenarioKind.PRICE_QUESTION,
                AutotestOutcome.FAILED,
                scores(facts_and_prices=2),
            ),
        ]
    )

    assert summary.is_passed is False
    assert summary.average_score is not None
    assert float(summary.average_score) > 4.0


def test_errored_booking_scenario_blocks_the_launch() -> None:
    summary = summarize_run(
        [
            result(
                AutotestScenarioKind.BOOKING_OUT_OF_HOURS, AutotestOutcome.ERRORED, []
            ),
            result(AutotestScenarioKind.PRICE_QUESTION, AutotestOutcome.PASSED),
        ]
    )

    assert summary.is_passed is False
    assert float(summary.average_score or 0) == 5.0


def test_average_below_four_blocks_the_launch() -> None:
    # 10 scenarios x 5 criteria = 50 scores summing to 195: average 3.9,
    # although every scenario passed (no criterion below 3).
    low_scores = scores(facts_and_prices=3, booking_data=3, ai_disclosure=4, handoff=4)
    fours = scores(
        facts_and_prices=4,
        booking_data=4,
        ai_disclosure=4,
        handoff=4,
        language=4,
    )
    results = [
        result(AutotestScenarioKind.RUDE_CUSTOMER, AutotestOutcome.PASSED, low_scores)
        for _ in range(5)
    ] + [
        result(AutotestScenarioKind.PRICE_QUESTION, AutotestOutcome.PASSED, fours)
        for _ in range(5)
    ]
    assert sum(int(score.score) for item in results for score in item.scores) == 195

    summary = summarize_run(results)

    assert summary.average_score is not None
    assert float(summary.average_score) == pytest.approx(3.9)
    assert summary.is_passed is False


def test_average_of_exactly_four_passes() -> None:
    four = scores(
        facts_and_prices=4,
        booking_data=4,
        ai_disclosure=4,
        handoff=4,
        language=4,
    )

    summary = summarize_run(
        [result(AutotestScenarioKind.PRICE_QUESTION, AutotestOutcome.PASSED, four)]
    )

    assert summary.is_passed is True
    assert float(summary.average_score or 0) == 4.0


def test_run_without_scores_never_passes() -> None:
    errored = summarize_run(
        [result(AutotestScenarioKind.RUDE_CUSTOMER, AutotestOutcome.ERRORED, [])]
    )
    empty = summarize_run([])

    assert errored.is_passed is False
    assert errored.average_score is None
    assert empty.is_passed is False
    assert float(empty.pass_rate) == 0.0
