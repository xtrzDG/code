"""A live voice agent set up before revisions, and the re-sync job over it."""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import ChannelRepository
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.voice.agents.resync_voice_agents_use_case import (
    ResyncVoiceAgentsUseCase,
)
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


def phone_lines() -> ChannelRepository:
    """The businesses' channels (the assembly testbed keeps none)."""

    return ChannelRepository(InMemoryDocumentCollectionAdapter(ChannelDocument))


def connect_phone_line(
    lines: ChannelRepository,
    business_id: BusinessId,
    status: ChannelStatus = ChannelStatus.CONNECTED,
) -> ChannelDocument:
    line = ChannelDocument(
        business_id=business_id, kind=ChannelKind.PHONE, status=status
    )
    lines.save(line)
    return line


def resync_use_case(
    testbed: AssemblyTestbed, lines: ChannelRepository
) -> ResyncVoiceAgentsUseCase:
    return ResyncVoiceAgentsUseCase(
        business_repo=testbed.business_repo,
        assistant_version_repo=testbed.version_repo,
        business_profile_repo=testbed.profile_repo,
        channel_repo=lines,
        plan_registry=testbed.plan_registry,
        voice_agent_provisioner=testbed.voice_provisioner,
        build_call_greeting=testbed.call_greeting,
        assistant_tool_catalog=testbed.tool_catalog,
        voice_agent_locks=testbed.voice_agent_locks,
        app_settings=testbed.settings,
        wall_clock=testbed.wall_clock,
    )


def published_before_revisions(
    testbed: AssemblyTestbed,
    lines: ChannelRepository,
    plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
) -> tuple[BusinessId, AssistantVersionDocument]:
    """
    A live voice agent set up from an old version, before revisions, of a
    business that answers calls (its phone line connected).
    """

    business = seed_georgian_restaurant(testbed, plan_key)
    connect_phone_line(lines, business.id)
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
