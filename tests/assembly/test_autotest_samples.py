"""pass^k: launch-critical scenarios are played twice and pass only if both pass."""

from collections.abc import Mapping

from app.schemas.constants.assistants import AutotestOutcome, AutotestScenarioKind
from app.schemas.typings.assistants.constrained_integers import AutotestSampleCount
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.utilities.assembly.autotest_samples import merge_sample_results
from tests.assembly.autotest_run_helpers import results_by_key, start
from tests.assembly.judge_helpers import PERFECT, result, scores
from tests.assembly.testbed import AssemblyTestbed

FAILING: dict[str, int] = {**PERFECT, "facts_and_prices": 2}
PASS_K: dict[str, str] = {"AUTOTEST_CRITICAL_SAMPLES": "2"}


class SecondPlayFails(dict[str, dict[str, int]]):
    """Judge scores whose second look at one scenario fails it."""

    def __init__(self, scenario_key: str) -> None:
        super().__init__()
        self._key: str = scenario_key
        self._looks: int = 0

    def get(  # type: ignore[override]
        self, key: str, default: Mapping[str, int] | None = None
    ) -> Mapping[str, int] | None:
        if key != self._key:
            return default

        self._looks += 1
        return {**(default or {}), **FAILING} if self._looks == 2 else default


def test_a_single_planned_play_is_reported_as_it_is() -> None:
    play = result(AutotestScenarioKind.RUDE_CUSTOMER, AutotestOutcome.PASSED)

    assert merge_sample_results([play], AutotestSampleCount(1)) == play


def test_the_failing_play_is_reported_with_every_plays_cost() -> None:
    passed = result(AutotestScenarioKind.BOOKING, AutotestOutcome.PASSED)
    failed = result(
        AutotestScenarioKind.BOOKING, AutotestOutcome.FAILED, scores(booking_data=2)
    ).model_copy(update={"cost_micro_usd": CostMicroUsd(30)})

    merged = merge_sample_results(
        [passed.model_copy(update={"cost_micro_usd": CostMicroUsd(20)}), failed],
        AutotestSampleCount(2),
    )

    assert merged.outcome is AutotestOutcome.FAILED
    assert merged.scores == failed.scores
    assert int(merged.cost_micro_usd) == 50
    assert merged.sample_count == AutotestSampleCount(2)
    assert merged.passed_sample_count is not None
    assert int(merged.passed_sample_count) == 1


def test_critical_scenarios_are_played_twice_and_others_once() -> None:
    testbed = AssemblyTestbed(PASS_K)
    business, version = start(testbed)
    testbed.judge_scores["booking__ru"] = FAILING

    results = results_by_key(testbed.run_autotests(business.id, version.id))

    booking = results["booking__ka"]
    assert (booking.sample_count, booking.passed_sample_count) == (2, 2)
    # The plays stop at the first that does not pass.
    failed = results["booking__ru"]
    assert failed.outcome is AutotestOutcome.FAILED
    assert (failed.sample_count, failed.passed_sample_count) == (1, 0)
    assert results["rude_customer__ka"].sample_count is None
    attack = results["tool_abuse__en"]
    assert (attack.sample_count, attack.passed_sample_count) == (2, 2)


def test_a_scenario_that_passes_once_and_fails_once_fails() -> None:
    testbed = AssemblyTestbed(PASS_K)
    business, version = start(testbed)
    testbed.judge_scores = SecondPlayFails("booking__en")

    run = testbed.run_autotests(business.id, version.id)

    flaky = results_by_key(run)["booking__en"]
    assert flaky.outcome is AutotestOutcome.FAILED
    assert (flaky.sample_count, flaky.passed_sample_count) == (2, 1)
    assert run.is_passed is False
