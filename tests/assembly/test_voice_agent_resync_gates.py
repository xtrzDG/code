"""
resync_voice_agents sets up only agents that serve calls now: an agent
removed on purpose (a pause, a plan without voice, a disconnected line) is
never created anew, and a failing voice platform costs a bounded run.
"""

import pytest

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.voice.agents import resync_voice_agents_use_case
from tests.assembly.testbed import AssemblyTestbed
from tests.assembly.voice_resync_helpers import (
    TICK,
    phone_lines,
    published_before_revisions,
    resync_use_case,
)


def pause(testbed: AssemblyTestbed, business_id: BusinessId) -> None:
    business: BusinessDocument | None = testbed.business_repo.get(business_id)
    assert business is not None
    business.status = BusinessStatus.PAUSED
    testbed.business_repo.save(business)


def test_a_paused_business_gets_no_agent_again() -> None:
    testbed = AssemblyTestbed()
    lines = phone_lines()
    business_id, old = published_before_revisions(testbed, lines)
    pause(testbed, business_id)
    assert old.voice_agent_id is not None
    # What pausing does (RemoveVoiceAgentUseCase).
    testbed.voice_provisioner.remove_agent(old.voice_agent_id)

    report = resync_use_case(testbed, lines).run(TICK)

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []
    stored = testbed.version_repo.get(business_id, old.id)
    assert stored is not None and stored.voice_agent_revision is None


def test_a_business_on_a_plan_without_voice_gets_no_agent_again() -> None:
    testbed = AssemblyTestbed()
    lines = phone_lines()
    business_id, _ = published_before_revisions(testbed, lines)
    business = testbed.business_repo.get(business_id)
    assert business is not None
    business.plan_key = PlanKey.CHAT
    testbed.business_repo.save(business)

    report = resync_use_case(testbed, lines).run(TICK)

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []


@pytest.mark.parametrize("status", [ChannelStatus.DISABLED, None])
def test_a_business_without_a_connected_line_gets_no_agent_again(
    status: ChannelStatus | None,
) -> None:
    testbed = AssemblyTestbed()
    lines = phone_lines()
    business_id, _ = published_before_revisions(testbed, lines)
    [line] = lines.list_by_business(business_id)
    other_lines = phone_lines()
    if status is not None:
        line.status = status
        other_lines.save(line)

    report = resync_use_case(testbed, other_lines).run(TICK)

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []


def test_a_failing_voice_platform_stops_the_run_at_the_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = AssemblyTestbed()
    lines = phone_lines()
    published_before_revisions(testbed, lines)
    published_before_revisions(testbed, lines)
    monkeypatch.setattr(resync_voice_agents_use_case, "MAX_AGENTS_PER_RUN", 1)
    testbed.voice_provisioner.error = ExternalServiceError("ElevenLabs said 503.")

    report = resync_use_case(testbed, lines).run(TICK)

    assert int(report.processed_count) == 0
    # One attempt, refused: the second business waits for the next run.
    assert len(testbed.voice_provisioner.specs) == 1
