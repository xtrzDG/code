import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.assistant_assembly import AssistantToolCatalogContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import (
    VoiceAgentLockRegistryContract,
    VoiceAgentProvisionerAdapterContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.use_cases.shared.business_walk import walk_businesses
from app.use_cases.shared.voice_agent_setup import VoiceAgentSetup
from app.utilities.assembly.voice_agents import (
    VOICE_AGENT_REVISION,
    needs_voice_agent_resync,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
# Each re-sync calls the voice platform a dozen times: a run sets up at most
# this many agents, and the next run goes on.
MAX_AGENTS_PER_RUN: int = 50
# An agent being published now is skipped; the next run takes it if needed.
RESYNC_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(2)


class ResyncVoiceAgentsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The periodic job `resync_voice_agents` (hourly, once per period across
    workers): the voice agent of every live version set up before the
    platform's current VOICE_AGENT_REVISION is set up again from that same
    version, so an agent published before list_my_bookings or
    decline_recording gets them without the owner publishing anew. The
    version then records the revision, and the next runs skip it.

    Each agent is set up under the agent's lock that publishing holds too,
    with the business and its live version read again inside it: a version
    published meanwhile is never overwritten by the one going out (a
    publish in progress makes this run skip the business). Nothing runs
    while the voice platform is not configured on this server. A run sets
    up at most MAX_AGENTS_PER_RUN agents; an agent the platform refused is
    logged and tried again on the next run. The report counts the agents
    set up.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        voice_agent_provisioner: VoiceAgentProvisionerAdapterContract,
        build_call_greeting: UseCaseContract[CallGreetingRequest, CallGreeting],
        assistant_tool_catalog: AssistantToolCatalogContract,
        voice_agent_locks: VoiceAgentLockRegistryContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._version_repo: AssistantVersionRepoContract = assistant_version_repo
        self._setup: VoiceAgentSetup = VoiceAgentSetup(
            business_profile_repo,
            voice_agent_provisioner,
            build_call_greeting,
            assistant_tool_catalog,
            app_settings,
        )
        self._locks: VoiceAgentLockRegistryContract = voice_agent_locks
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        if not self._setup.is_configured():
            return JobReport()

        synced: int = 0
        for business in walk_businesses(self._business_repo):
            if synced >= MAX_AGENTS_PER_RUN:
                break

            if self._live_version(business) is None:
                continue

            try:
                with self._locks.lock_agent(business.id, RESYNC_LOCK_WAIT):
                    synced += int(self._resync(business.id))
            except ApplicationError as error:
                LOGGER.warning(
                    "The voice agent of %s was not re-synced: %s", business.id, error
                )

        return JobReport(processed_count=ProcessedItemCount(synced))

    def _live_version(
        self, business: BusinessDocument
    ) -> AssistantVersionDocument | None:
        """The business's live version when its agent needs a re-sync."""

        if business.published_assistant_version_id is None:
            return None

        version: AssistantVersionDocument | None = self._version_repo.get(
            business.id, business.published_assistant_version_id
        )
        if version is None or not needs_voice_agent_resync(version):
            return None

        return version

    def _resync(self, business_id: BusinessId) -> bool:
        """Set the agent up again from the live version as stored now."""

        business: BusinessDocument | None = self._business_repo.get(business_id)
        version: AssistantVersionDocument | None = (
            None if business is None else self._live_version(business)
        )
        if business is None or version is None:
            return False

        agent_id: VoiceAgentId = self._setup.set_up(
            business, version, version.voice_agent_id
        )
        now: Microseconds = self._wall_clock.now_unix()

        def record(stored: AssistantVersionDocument) -> AssistantVersionDocument:
            stored.voice_agent_id = agent_id
            stored.voice_agent_revision = VOICE_AGENT_REVISION
            stored.updated_at = now
            return stored

        return self._version_repo.modify(business_id, version.id, record) is not None
