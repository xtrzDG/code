"""A version's autotest run against the run of the version that is live."""

from app.schemas.constants.assistants import (
    AutotestOutcome,
    AutotestRunStatus,
    JudgeCriterion,
)
from app.schemas.dto.assistants.assistant_commands import AssistantVersionQuery
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.publish_helpers import ready_version
from tests.assembly.testbed import AssemblyTestbed

FAILING: dict[str, int] = {criterion.value: 5 for criterion in JudgeCriterion} | {
    "facts_and_prices": 2
}
LOWER: dict[str, int] = {criterion.value: 5 for criterion in JudgeCriterion} | {
    "handoff": 3,
    "language": 4,
}


def shown_run(
    testbed: AssemblyTestbed, business_id: BusinessId, version_id: AssistantVersionId
) -> AutotestRunView:
    business = testbed.business(business_id)
    return testbed.get_autotest_run_use_case.run(
        AssistantVersionQuery(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version_id,
        )
    )


def test_the_first_version_has_nothing_to_compare_with() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = ready_version(testbed, business)

    shown = shown_run(testbed, business.id, version.id)

    assert shown.comparison is None
    run = testbed.run_repo.get(business.id, shown.id)
    assert run is not None
    assert run.compared_to_run_id is None


def test_a_new_version_shows_new_failures_and_score_changes_against_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    live = ready_version(testbed, business)
    testbed.publish(business.id, live.id)
    live_run = shown_run(testbed, business.id, live.id)
    testbed.judge_scores["booking__it"] = FAILING
    testbed.judge_scores["unknown_question__en"] = LOWER

    draft = testbed.assemble(business.id)
    testbed.run_autotests(business.id, draft.id)
    shown = shown_run(testbed, business.id, draft.id)

    stored = testbed.run_repo.get(business.id, shown.id)
    assert stored is not None
    assert stored.compared_to_run_id == live_run.id
    comparison = shown.comparison
    assert comparison is not None
    assert comparison.baseline_run_id == live_run.id
    assert comparison.baseline_version_id == live.id
    assert comparison.baseline_version_number == live.version_number
    assert comparison.shared_scenario_count == len(live_run.results)
    assert [str(change.scenario_key) for change in comparison.new_failures] == [
        "booking__it"
    ]
    failure = comparison.new_failures[0]
    assert failure.outcome is AutotestOutcome.FAILED
    assert failure.baseline_outcome is AutotestOutcome.PASSED
    assert comparison.fixed == []
    assert [str(change.scenario_key) for change in comparison.score_changes] == [
        "booking__it",
        "unknown_question__en",
    ]
    assert float(comparison.score_changes[0].change) == -0.6
    assert float(comparison.score_changes[1].change) == -0.6
    assert comparison.average_score_change is not None
    assert float(comparison.average_score_change) < 0
    criteria = {change.criterion: change for change in comparison.criterion_changes}
    assert set(criteria) == set(JudgeCriterion)
    assert float(criteria[JudgeCriterion.FACTS_AND_PRICES].change) < 0
    assert float(criteria[JudgeCriterion.BOOKING_DATA].change) == 0


def test_a_fixed_scenario_is_listed_and_a_running_run_is_not_compared() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    testbed.judge_scores["booking__en"] = FAILING
    live = testbed.assemble(business.id, run_autotests=True)
    testbed.publish(
        business.id,
        live.id,
        accept_failed_tests=True,
        user_id=testbed.add_platform_admin(business.id),
    )
    del testbed.judge_scores["booking__en"]

    draft = testbed.assemble(business.id)
    testbed.run_autotests(business.id, draft.id)
    shown = shown_run(testbed, business.id, draft.id)

    comparison = shown.comparison
    assert comparison is not None
    assert comparison.new_failures == []
    assert [str(change.scenario_key) for change in comparison.fixed] == ["booking__en"]
    assert comparison.fixed[0].baseline_outcome is AutotestOutcome.FAILED
    assert comparison.fixed[0].check_codes == []

    stored = testbed.run_repo.get(business.id, shown.id)
    assert stored is not None
    stored.status = AutotestRunStatus.RUNNING
    testbed.run_repo.save(stored)
    assert shown_run(testbed, business.id, draft.id).comparison is None


def test_a_live_run_that_never_finished_is_not_compared() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    live = ready_version(testbed, business)
    testbed.publish(business.id, live.id)
    draft = testbed.assemble(business.id)
    testbed.run_autotests(business.id, draft.id)
    live_run = testbed.run_repo.get(
        business.id, shown_run(testbed, business.id, live.id).id
    )
    assert live_run is not None
    live_run.status = AutotestRunStatus.ERRORED
    testbed.run_repo.save(live_run)

    assert shown_run(testbed, business.id, draft.id).comparison is None
