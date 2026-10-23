"""resync_voice_agents: agents set up before the current revision get set up again."""

import threading

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.jobs import JobReport
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.utilities.assembly.voice_agents import VOICE_AGENT_REVISION
from tests.assembly.testbed import AssemblyTestbed
from tests.assembly.voice_resync_helpers import (
    OLD_TOOLS,
    TICK,
    phone_lines,
    published_before_revisions,
    resync_use_case,
)


def test_an_old_agent_gets_the_new_tools_without_a_new_publish() -> None:
    testbed = AssemblyTestbed()
    lines = phone_lines()
    business_id, old = published_before_revisions(testbed, lines)

    report: JobReport = resync_use_case(testbed, lines).run(TICK)

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
    lines = phone_lines()
    published_before_revisions(testbed, lines)
    resync = resync_use_case(testbed, lines)
    resync.run(TICK)
    testbed.voice_provisioner.specs.clear()

    report = resync.run(TICK)

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []


def test_nothing_runs_while_the_voice_platform_is_not_configured() -> None:
    testbed = AssemblyTestbed()
    lines = phone_lines()
    published_before_revisions(testbed, lines)
    testbed.voice_provisioner.missing_settings = [
        EnvironmentVariableName("ELEVENLABS_API_KEY")
    ]

    report = resync_use_case(testbed, lines).run(TICK)

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []


def test_a_refused_agent_is_tried_again_on_the_next_run() -> None:
    testbed = AssemblyTestbed()
    lines = phone_lines()
    business_id, old = published_before_revisions(testbed, lines)
    testbed.voice_provisioner.error = ExternalServiceError("ElevenLabs said 503.")
    resync = resync_use_case(testbed, lines)

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
    lines = phone_lines()
    business_id, _ = published_before_revisions(testbed, lines)
    probe = LockProbe(testbed, business_id)
    testbed.voice_provisioner.on_upsert = probe.probe

    resync_use_case(testbed, lines).run(TICK)

    # While the platform was called, a publish (another thread) had to wait.
    assert probe.was_free is False


def test_a_business_being_published_is_skipped_this_run() -> None:
    testbed = AssemblyTestbed()
    lines = phone_lines()
    business_id, old = published_before_revisions(testbed, lines)
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
        report = resync_use_case(testbed, lines).run(TICK)
    finally:
        release.set()
        publisher.join()

    assert int(report.processed_count) == 0
    assert testbed.voice_provisioner.specs == []
    stored = testbed.version_repo.get(business_id, old.id)
    assert stored is not None and stored.voice_agent_revision is None
