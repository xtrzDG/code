"""
An autotest run queued before a platform brake (the global pause, the
daily budget stop) checks it when the worker starts it: while the brake
holds it plays no model turn, ends ERRORED and gives its version back the
status it had, so the owner can run it again once the brake lifts.
"""

import pytest

from app.schemas.constants.assistants import AssistantVersionStatus, AutotestRunStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.spend import PlatformBrake
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.assembly.autotest_run_helpers import start
from tests.assembly.testbed import AssemblyTestbed


def queue(
    testbed: AssemblyTestbed, business_id: BusinessId, version_id: AssistantVersionId
) -> AutotestRunView:
    return testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id, business_id=business_id, version_id=version_id
        )
    )


@pytest.mark.parametrize("brake", [PlatformBrake.PAUSED, PlatformBrake.BUDGET_STOP])
def test_a_run_queued_before_a_brake_is_skipped_when_it_starts(
    brake: PlatformBrake,
) -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    status_before: AssistantVersionStatus = testbed.version(
        business.id, version.id
    ).status
    queued = queue(testbed, business.id, version.id)
    testbed.platform_brakes.brake = brake

    tick = testbed.run_worker()

    assert (tick.queued_runs, tick.failures) == (1, 0)
    assert testbed.platform_brakes.readings, "the brake is read as the run starts"
    assert testbed.conversation.inbound_messages == []
    stored = testbed.run_repo.get(business.id, queued.id)
    assert stored is not None
    assert (stored.status, stored.results) == (AutotestRunStatus.ERRORED, [])
    assert testbed.version(business.id, version.id).status is status_before
    assert [
        (event.event, list(event.ids))
        for event in testbed.autotest_events.events
        if event.event is LiveEventKind.AUTOTEST_PROGRESS
    ][-1] == (LiveEventKind.AUTOTEST_PROGRESS, [queued.id, version.id])


def test_once_the_brake_lifts_the_run_can_start_again() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    skipped = queue(testbed, business.id, version.id)
    testbed.platform_brakes.brake = PlatformBrake.PAUSED
    testbed.run_worker()
    testbed.platform_brakes.brake = None

    again = queue(testbed, business.id, version.id)
    testbed.run_worker()

    assert again.id != skipped.id
    stored = testbed.run_repo.get(business.id, again.id)
    assert stored is not None
    assert stored.status is AutotestRunStatus.FINISHED
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.READY
    )


def test_without_a_brake_the_queued_run_plays() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    queued = queue(testbed, business.id, version.id)

    testbed.run_worker()

    stored = testbed.run_repo.get(business.id, queued.id)
    assert stored is not None
    assert stored.status is AutotestRunStatus.FINISHED
    assert testbed.platform_brakes.readings
