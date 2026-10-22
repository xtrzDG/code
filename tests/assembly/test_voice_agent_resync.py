"""resync_voice_agents: agents set up before the current revision get set up again."""

import threading

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.billing import PlanKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import (
    EnvironmentVariableName,
    JobName,
)
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.use_cases.voice.agents.resync_voice_agents_use_case import (
    ResyncVoiceAgentsUseCase,
)
from app.utilities.assembly.voice_agents import VOICE_AGENT_REVISION
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.publish_helpers import ready_version
from tests.assembly.testbed import AssemblyTestbed

TICK = JobTick(job_name=JobName("resync_voice_agents"), scheduled_at=Microseconds(0))
# What a version assembled before list_my_bookings and join_waitlist held.
OLD_TOOLS: list[AssistantToolName] = [
    AssistantToolName.SEARCH_KNOWLEDGE,
    AssistantToolName.CHECK_AVAILABILITY,
    AssistantToolName.CREATE_BOOKING,
    AssistantToolName.CANCEL_BOOKING,
    AssistantToolName.HANDOFF_TO_HUMAN,
]


def resync_use_case(testbed: AssemblyTestbed) -> ResyncVoiceAgentsUseCase:
    return ResyncVoiceAgentsUseCase(
        business_repo=testbed.business_repo,
        assistant_version_repo=testbed.version_repo,
        business_profile_repo=testbed.profile_repo,
        voice_agent_provisioner=testbed.voice_provisioner,
        build_call_greeting=testbed.call_greeting,
        assistant_tool_catalog=testbed.tool_catalog,
        voice_agent_locks=testbed.voice_agent_locks,
        app_settings=testbed.settings,
        wall_clock=testbed.wall_clock,
    )


def published_before_revisions(
    testbed: AssemblyTestbed,
) -> tuple[BusinessId, AssistantVersionDocument]:
    """A live voice agent set up from an old version, before revisions."""

    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)
    testbed.publish(business.id, version.id)

    def make_old(stored: AssistantVersionDocument) -> AssistantVersionDocument:
        stored.tools = list(OLD_TOOLS)
        stored.voice_agent_revision = None
        return stored

    old = testbed.version_repo.modify(business.id, version.id, make_old)
    assert old is not None and old.voice_agent_id is not None
    testbed.voice_provisioner.specs.clear()
    return business.id, old


def test_an_old_agent_gets_the_new_tools_without_a_new_publish() -> None:
    testbed = AssemblyTestbed()
    business_id, old = published_before_revisions(testbed)

    report: JobReport = resync_use_case(testbed).run(TICK)

    assert int(report.processed_count) == 1
    [spec] = testbed.voice_provisioner.specs
    assert spec.existing_agent_id == old.voice_agent_id
    assert spec.prompt_text == old.phone_prompt_text
    assert [tool.name for tool in spec.tools] == [
        AssistantToolName.SEARCH_KNOWLEDGE,
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
        AssistantToolName.CANCEL_BOOKING,
        AssistantToolName.LIST_MY_BOOKINGS,
        AssistantToolName.JOIN_WAITLIST,
        AssistantToolName.HANDOFF_TO_HUMAN,
        AssistantToolName.DECLINE_RECORDING,
    ]
    synced = testbed.version_repo.get(business_id, old.id)
    assert synced is not None
    assert synced.voice_agent_revision == VOICE_AGENT_REVISION
    assert synced.tools == OLD_TOOLS


def test_a_synced_agent_is_left_alone() -> None:
    testbed = AssemblyTestbed()
    published_before_revisions(testbed)
    resync = resync_use_case(testbed)
    resync.run(TICK)
    testbed.voice_provisioner.specs.clear()

    report = resync.run(TICK)

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []


def test_nothing_runs_while_the_voice_platform_is_not_configured() -> None:
    testbed = AssemblyTestbed()
    published_before_revisions(testbed)
    testbed.voice_provisioner.missing_settings = [
        EnvironmentVariableName("ELEVENLABS_API_KEY")
    ]

    report = resync_use_case(testbed).run(TICK)

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []


def test_a_refused_agent_is_tried_again_on_the_next_run() -> None:
    testbed = AssemblyTestbed()
    business_id, old = published_before_revisions(testbed)
    testbed.voice_provisioner.error = ExternalServiceError("ElevenLabs said 503.")
    resync = resync_use_case(testbed)

    failed = resync.run(TICK)

    assert int(failed.processed_count) == 0
    stored = testbed.version_repo.get(business_id, old.id)
    assert stored is not None and stored.voice_agent_revision is None
    testbed.voice_provisioner.error = None
    assert int(resync.run(TICK).processed_count) == 1


class LockProbe:
    """Checks, from another thread, whether the agent's lock is free now."""

    def __init__(self, testbed: AssemblyTestbed, business_id: BusinessId) -> None:
        self._testbed = testbed
        self._business_id = business_id
        self.was_free: bool | None = None

    def probe(self) -> None:
        def try_lock() -> None:
            try:
                with self._testbed.voice_agent_locks.lock_agent(
                    self._business_id, LockWaitSeconds(1)
                ):
                    self.was_free = True
            except ExternalServiceError:
                self.was_free = False

        other = threading.Thread(target=try_lock)
        other.start()
        other.join()


def test_the_agent_is_set_up_under_the_lock_publishing_holds() -> None:
    testbed = AssemblyTestbed()
    business_id, _ = published_before_revisions(testbed)
    probe = LockProbe(testbed, business_id)
    testbed.voice_provisioner.on_upsert = probe.probe

    resync_use_case(testbed).run(TICK)

    # While the platform was called, a publish (another thread) had to wait.
    assert probe.was_free is False


def test_a_business_being_published_is_skipped_this_run() -> None:
    testbed = AssemblyTestbed()
    business_id, old = published_before_revisions(testbed)
    holding = threading.Event()
    release = threading.Event()

    def publish_in_progress() -> None:
        with testbed.voice_agent_locks.lock_agent(business_id, LockWaitSeconds(1)):
            holding.set()
            release.wait()

    publisher = threading.Thread(target=publish_in_progress)
    publisher.start()
    holding.wait()
    try:
        report = resync_use_case(testbed).run(TICK)
    finally:
        release.set()
        publisher.join()

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []
    stored = testbed.version_repo.get(business_id, old.id)
    assert stored is not None and stored.voice_agent_revision is None
