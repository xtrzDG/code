"""
A complete in-memory conversation engine for tests: real repositories over
InMemoryDocumentCollectionAdapter, the real language detector, phone parser,
tool registry and localized texts; fake tool use cases, a fake claim check
(`GuardOptions`) and a scripted language model. The clock is manual. The
parts are built by brain_repositories, brain_business_seed, brain_tools and
brain_orchestrators.
"""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds, WallClock

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.contracts.llm import LlmAdapterContract
from app.orchestrators.conversations.conversation_turn_orchestrator import (
    ConversationTurnOrchestrator,
)
from app.orchestrators.conversations.voice_tool_call_orchestrator import (
    VoiceToolCallOrchestrator,
)
from app.pipelines.conversations.customer_message_pipeline import (
    CustomerMessagePipeline,
)
from app.registries.locks.customer_message_lock_registry import (
    CustomerMessageLockRegistry,
)
from app.registries.turns.turn_slot_registry import build_customer_turn_slots
from app.repositories.assistant_repositories import AssistantVersionRepository
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.booking_repositories import HandoffRepository
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.call_repository import CallRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.feedback_repositories import FeedbackRequestRepository
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ScheduleExceptionRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.knowledge import KnowledgeItemView
from app.schemas.typings.assistants.constrained_integers import LlmToolRoundLimit
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import ContactMessageLimit
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.conversations.build_call_greeting_use_case import (
    BuildCallGreetingUseCase,
)
from app.use_cases.conversations.tools.run_assistant_tool_use_case import (
    RunAssistantToolUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.brain.brain_business_seed import seed_business
from tests.brain.brain_orchestrators import GuardOptions, build_brain_orchestrators
from tests.brain.brain_repositories import build_brain_repositories
from tests.brain.brain_tools import build_brain_tools
from tests.brain.business_setups import GEORGIA, BusinessSetup, default_menu
from tests.brain.fake_booking_tools import FakeBookings, FakeCheckAvailability
from tests.brain.fake_contact_tools import (
    FakeCreateLead,
    FakeHandoff,
    FakeRecordUnansweredQuestion,
)
from tests.brain.fake_knowledge_tools import FakeGetPrice, FakeSearchKnowledge
from tests.brain.manual_clock import ManualClock
from tests.foundation.access_support import ACCESS_SETTINGS
from tests.foundation.support_access_builders import build_authorize_business_access
from tests.live_events.recording_event_publisher import RecordingEventPublisher

CUSTOMER_PHONE: E164PhoneNumber = E164PhoneNumber("+995555123456")


@dataclass
class BrainWorld:
    clock: ManualClock
    owner_id: UserId
    staff_id: UserId
    business: BusinessDocument
    version: AssistantVersionDocument
    llm: LlmAdapterContract
    business_repo: BusinessRepository
    profile_repo: BusinessProfileRepository
    exception_repo: ScheduleExceptionRepository
    version_repo: AssistantVersionRepository
    contact_repo: ContactRepository
    conversation_repo: ConversationRepository
    message_repo: MessageRepository
    llm_turn_repo: LlmTurnRepository
    usage_event_repo: UsageEventRepository
    handoff_repo: HandoffRepository
    channel_repo: ChannelRepository
    call_repo: CallRepository
    audit_log_repo: AuditLogRepository
    user_repo: UserRepository
    knowledge_item_repo: KnowledgeItemRepository
    feedback_request_repo: FeedbackRequestRepository
    bookings: FakeBookings
    search_knowledge: FakeSearchKnowledge
    get_price: FakeGetPrice
    availability: FakeCheckAvailability
    create_lead: FakeCreateLead
    handoff: FakeHandoff
    record_question: FakeRecordUnansweredQuestion
    run_tool: RunAssistantToolUseCase
    authorize: AuthorizeBusinessAccessUseCase
    orchestrator: ConversationTurnOrchestrator
    pipeline: CustomerMessagePipeline
    voice_orchestrator: VoiceToolCallOrchestrator
    greeting: BuildCallGreetingUseCase
    live_events: RecordingEventPublisher
    texts: LocalizedTextResolver = field(default_factory=LocalizedTextResolver)

    def send(
        self,
        text: str,
        *,
        channel: ChannelKind = ChannelKind.WHATSAPP,
        user_id: str = "995555123456",
        phone: E164PhoneNumber | None = CUSTOMER_PHONE,
        name: str | None = None,
        is_sandbox: bool = False,
        version_id: AssistantVersionId | None = None,
    ) -> AssistantReply:
        return self.pipeline.start(
            InboundMessage(
                business_id=self.business.id,
                channel=channel,
                channel_user_id=ChannelUserId(user_id),
                text=MessageText(text),
                contact_name=None if name is None else ContactName(name),
                contact_phone_number=phone,
                is_sandbox=is_sandbox,
                assistant_version_id=version_id,
            )
        )

    def conversations(self) -> list[ConversationDocument]:
        return self.conversation_repo.list_by_business(self.business.id)

    def messages(self, conversation_id: object) -> list[MessageDocument]:
        for conversation in self.conversations():
            if conversation.id == conversation_id:
                return self.message_repo.list_by_conversation(
                    self.business.id, conversation.id
                )

        return []

    def turns(self, conversation_id: object) -> list[LlmTurnDocument]:
        for conversation in self.conversations():
            if conversation.id == conversation_id:
                return self.llm_turn_repo.list_by_conversation(conversation.id)

        return []

    def usage_events(self) -> list[UsageEventDocument]:
        return self.usage_event_repo.list_by_business_between(
            self.business.id,
            Microseconds(0),
            Microseconds(2**62),
        )

    def contacts(self) -> list[ContactDocument]:
        return self.contact_repo.list_by_business(self.business.id)

    def handoffs(self) -> list[HandoffDocument]:
        return self.handoff_repo.list_by_business(self.business.id)

    def save_business(self, business: BusinessDocument) -> None:
        self.business_repo.save(business)
        self.business = business


def build_world(
    llm: LlmAdapterContract,
    setup: BusinessSetup = GEORGIA,
    *,
    tools: list[AssistantToolName] | None = None,
    contact_message_limit: int = 60,
    tool_round_limit: int = 4,
    knowledge: list[KnowledgeItemView] | None = None,
    facts: list[tuple[str, str, str]] | None = None,
    hours: list[tuple[int, int]] | None = None,
    is_published: bool = True,
    app_base_url: str | None = None,
    guard: GuardOptions | None = None,
) -> BrainWorld:
    clock = ManualClock()
    wall_clock: WallClock[Microseconds] = clock.wall_clock()
    repos = build_brain_repositories()
    seeded = seed_business(
        repos,
        setup,
        tools=tools,
        facts=facts,
        hours=hours,
        is_published=is_published,
    )
    items = knowledge if knowledge is not None else default_menu(setup)
    brain_tools = build_brain_tools(repos, seeded.business, items, wall_clock)
    texts = LocalizedTextResolver()
    orchestrators = build_brain_orchestrators(
        llm,
        repos,
        brain_tools,
        texts,
        wall_clock,
        contact_message_limit=ContactMessageLimit(contact_message_limit),
        tool_round_limit=LlmToolRoundLimit(tool_round_limit),
        app_base_url=None if app_base_url is None else PublicBaseUrl(app_base_url),
        guard=guard or GuardOptions(),
    )
    return BrainWorld(
        clock=clock,
        owner_id=seeded.owner_id,
        staff_id=seeded.staff_id,
        business=seeded.business,
        version=seeded.version,
        llm=llm,
        business_repo=repos.business_repo,
        profile_repo=repos.profile_repo,
        exception_repo=repos.exception_repo,
        version_repo=repos.version_repo,
        contact_repo=repos.contact_repo,
        conversation_repo=repos.conversation_repo,
        message_repo=repos.message_repo,
        llm_turn_repo=repos.llm_turn_repo,
        usage_event_repo=repos.usage_event_repo,
        channel_repo=repos.channel_repo,
        call_repo=repos.call_repo,
        handoff_repo=repos.handoff_repo,
        audit_log_repo=repos.audit_log_repo,
        user_repo=repos.user_repo,
        knowledge_item_repo=repos.knowledge_item_repo,
        feedback_request_repo=repos.feedback_request_repo,
        bookings=brain_tools.bookings,
        search_knowledge=brain_tools.search_knowledge,
        get_price=brain_tools.get_price,
        availability=brain_tools.availability,
        create_lead=brain_tools.create_lead,
        handoff=brain_tools.handoff,
        record_question=brain_tools.record_question,
        run_tool=brain_tools.run_tool,
        authorize=build_authorize_business_access(
            business_repo=repos.business_repo,
            user_repo=repos.user_repo,
            audit_log_repo=repos.audit_log_repo,
            wall_clock=wall_clock,
            session_assurance=SessionAssuranceContext(),
            app_settings=ACCESS_SETTINGS,
        ),
        orchestrator=orchestrators.orchestrator,
        pipeline=CustomerMessagePipeline(
            orchestrators.orchestrator,
            CustomerMessageLockRegistry(InMemoryAdvisoryLockAdapter()),
            build_customer_turn_slots(assemble_app_settings({})),
        ),
        voice_orchestrator=orchestrators.voice_orchestrator,
        greeting=BuildCallGreetingUseCase(
            business_repo=repos.business_repo,
            localized_text_resolver=texts,
        ),
        texts=texts,
        live_events=orchestrators.live_events,
    )
