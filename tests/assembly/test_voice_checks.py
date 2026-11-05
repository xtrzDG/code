"""
The voice checks of autotests: a version with voice is tested by a
simulated call in each of its languages (ka, ru and en for the Tbilisi
restaurant), stored as results with the channel PHONE, and a version whose
calls book wrongly cannot go live.
"""

import pytest

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestCheckCode,
    AutotestOutcome,
    AutotestRunStatus,
    AutotestScenarioKind,
)
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.assembly.fake_voice_checks import booking_call
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.publish_helpers import reason_codes
from tests.assembly.testbed import AssemblyTestbed


def voice_ready(environment: dict[str, str] | None = None) -> AssemblyTestbed:
    """A testbed whose voice platform can play the checks."""

    testbed = AssemblyTestbed(environment)
    testbed.voice_checks.missing_settings = []
    return testbed


def run_results(
    testbed: AssemblyTestbed, business_id: BusinessId, version_id: AssistantVersionId
) -> list[AutotestScenarioResult]:
    run_id = testbed.version(business_id, version_id).autotest_run_id
    assert run_id is not None
    run = testbed.run_repo.get(business_id, run_id)
    assert run is not None
    return list(run.results)


def phone_results(
    testbed: AssemblyTestbed, business_id: BusinessId, version_id: AssistantVersionId
) -> list[AutotestScenarioResult]:
    return [
        result
        for result in run_results(testbed, business_id, version_id)
        if result.channel is ChannelKind.PHONE
    ]


def test_a_voice_version_is_checked_by_a_call_in_each_language() -> None:
    testbed = voice_ready()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)

    version = testbed.assemble(business.id, run_autotests=True)

    assert version.status is AssistantVersionStatus.READY
    [batch] = testbed.voice_checks.batches
    assert [str(case.language) for case in batch.cases] == ["ka", "ru", "en"]
    # The agent of the checks is the one publishing would build.
    assert [str(item.language) for item in batch.agent.voice_profiles] == [
        "ka",
        "ru",
        "en",
    ]
    assert "Georgian" in str(batch.cases[0].brief)
    assert AssistantToolName.CREATE_BOOKING in {
        mock.tool_name for mock in batch.cases[0].tool_mocks
    }
    results = phone_results(testbed, business.id, version.id)
    assert [(str(result.scenario_key), result.outcome) for result in results] == [
        ("phone__booking__ka", AutotestOutcome.PASSED),
        ("phone__booking__ru", AutotestOutcome.PASSED),
        ("phone__booking__en", AutotestOutcome.PASSED),
    ]
    assert all(result.kind is AutotestScenarioKind.BOOKING for result in results)
    assert sum(int(result.cost_micro_usd) for result in results) == 36_000


def test_a_call_that_books_wrongly_keeps_the_version_from_going_live() -> None:
    testbed = voice_ready()
    testbed.voice_checks.script = booking_call(party_size=5)
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)

    version = testbed.assemble(business.id, run_autotests=True)

    assert version.status is AssistantVersionStatus.TESTS_FAILED
    assert {
        result.outcome for result in phone_results(testbed, business.id, version.id)
    } == {AutotestOutcome.FAILED}
    with pytest.raises(ConflictError) as refusal:
        testbed.publish(business.id, version.id)
    assert ("autotests", ["tests_failed"]) in [
        (code, details[:1]) for code, details in reason_codes(refusal.value)
    ]


def test_a_voice_platform_that_fails_errs_the_checks_and_fails_the_run() -> None:
    testbed = voice_ready()
    testbed.voice_checks.error = ExternalServiceError("ElevenLabs said 503.")
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)

    version = testbed.assemble(business.id, run_autotests=True)

    assert version.status is AssistantVersionStatus.TESTS_FAILED
    results = phone_results(testbed, business.id, version.id)
    assert {result.outcome for result in results} == {AutotestOutcome.ERRORED}
    assert all(
        result.check_codes == [AutotestCheckCode.CONVERSATION_FAILED]
        for result in results
    )


@pytest.mark.parametrize(
    ("environment", "is_configured"),
    [
        ({"VOICE_CHECKS_ENABLED": "false"}, True),
        ({}, False),
    ],
)
def test_without_voice_checks_a_voice_version_is_tested_in_chat_only(
    environment: dict[str, str], is_configured: bool
) -> None:
    testbed = AssemblyTestbed(environment)
    if is_configured:
        testbed.voice_checks.missing_settings = []
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)

    version = testbed.assemble(business.id, run_autotests=True)

    assert version.status is AssistantVersionStatus.READY
    assert testbed.voice_checks.batches == []
    assert phone_results(testbed, business.id, version.id) == []


def test_a_chat_version_gets_no_voice_checks() -> None:
    testbed = voice_ready()
    business = seed_georgian_restaurant(testbed, PlanKey.CHAT)

    testbed.assemble(business.id, run_autotests=True)

    assert testbed.voice_checks.batches == []


def test_the_worker_counts_the_calls_in_the_run_and_plays_them_last() -> None:
    testbed = voice_ready()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = testbed.assemble(business.id)

    started = testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id, business_id=business.id, version_id=version.id
        )
    )
    testbed.run_worker()

    run = testbed.run_repo.get(business.id, started.id)
    assert run is not None
    assert run.status is AutotestRunStatus.FINISHED
    assert int(run.planned_scenario_count or 0) == len(run.results)
    channels = [result.channel for result in run.results]
    assert channels[-3:] == [ChannelKind.PHONE] * 3
    assert set(channels[:-3]) == {None}
