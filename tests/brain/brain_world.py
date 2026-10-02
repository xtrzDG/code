"""
A complete in-memory conversation engine for tests.

Real repositories over InMemoryDocumentCollectionAdapter, the real language
detector, phone parser, tool registry and localized texts; fake tool use
cases (tests/brain/fake_tools.py) and a scripted language model. The clock
is manual, so tests can move time forward.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from typed_time_provider import Microseconds, WallClock

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
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
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.tools.assistant_tool_registry import AssistantToolRegistry
from app.repositories.assistant_repositories import AssistantVersionRepository
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.booking_repositories import HandoffRepository
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    CallRepository,
    ContactRepository,
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ScheduleExceptionRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    LlmEffort,
)
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessLinkKind, BusinessStatus, Weekday
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.assistants import AssistantVersionDocument, BusinessFact
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument, OpeningInterval
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.knowledge import KnowledgeItemView
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
)
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmToolInputJson,
    MessageText,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.conversations.build_call_greeting_use_case import (
    BuildCallGreetingUseCase,
)
from app.use_cases.conversations.open_voice_conversation_use_case import (
    OpenVoiceConversationUseCase,
)
from app.use_cases.conversations.record_assistant_reply_use_case import (
    RecordAssistantReplyUseCase,
)
from app.use_cases.conversations.record_voice_tool_call_use_case import (
    RecordVoiceToolCallUseCase,
)
from app.use_cases.conversations.replies.generate_assistant_reply_use_case import (
    GenerateAssistantReplyUseCase,
)
from app.use_cases.conversations.tools.run_assistant_tool_use_case import (
    RunAssistantToolUseCase,
)
from app.use_cases.conversations.turns.prepare_conversation_turn_use_case import (
    PrepareConversationTurnUseCase,
)
from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.brain.fake_tools import (
    FakeBookings,
    FakeCancelBooking,
    FakeCheckAvailability,
    FakeCreateBooking,
    FakeCreateLead,
    FakeGetPrice,
    FakeHandoff,
    FakeRecordUnansweredQuestion,
    FakeRescheduleBooking,
    FakeSearchKnowledge,
    FakeSendLink,
)

# Thursday 2026-10-01 10:00 UTC = 14:00 in Tbilisi.
START_MOMENT: datetime = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
NANOSECONDS_PER_MICROSECOND: int = 1000
ALL_TOOLS: list[AssistantToolName] = list(AssistantToolName)
CUSTOMER_PHONE: E164PhoneNumber = E164PhoneNumber("+995555123456")


class ManualClock:
    """Wall clock whose time tests move by hand."""

    def __init__(self, start: datetime = START_MOMENT) -> None:
        self.moment: datetime = start

    def advance(self, delta: timedelta) -> None:
        self.moment += delta

    def now_nanoseconds(self) -> int:
        delta: timedelta = self.moment - datetime(1970, 1, 1, tzinfo=UTC)
        microseconds: int = (
            delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds
        )
        return microseconds * NANOSECONDS_PER_MICROSECOND

    def wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=self.now_nanoseconds,
        )


@dataclass(frozen=True)
class BusinessSetup:
    """A business of some country, as a test needs it."""

    name: str = "Sakhli"
    country_code: str = "GE"
    timezone: str = "Asia/Tbilisi"
    currency_code: str = "GEL"
    languages: tuple[str, ...] = ("ka", "ru", "en")
    status: BusinessStatus = BusinessStatus.LIVE


GEORGIA = BusinessSetup()
ISRAEL = BusinessSetup(
    name="Beit Kafe",
    country_code="IL",
    timezone="Asia/Jerusalem",
    currency_code="ILS",
    languages=("he", "ar", "en", "ru"),
)
ARMENIA = BusinessSetup(
    name="Ararat Grill",
    country_code="AM",
    timezone="Asia/Yerevan",
    currency_code="AMD",
    languages=("hy", "ru", "en"),
)
BRAZIL = BusinessSetup(
    name="Cantina Sol",
    country_code="BR",
    timezone="America/Sao_Paulo",
    currency_code="BRL",
    languages=("pt-BR", "en", "es"),
)


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


def scripted(*turns: ScriptedLlmTurn) -> ScriptedLlmAdapter:
    return ScriptedLlmAdapter.from_turns(list(turns))


def say(text: str) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(text=MessageText(text))


def call_tool(
    tool_name: AssistantToolName,
    input_json: str,
    text: str | None = None,
) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(
        text=None if text is None else MessageText(text),
        tool_calls=[
            ScriptedToolCall(
                tool_name=tool_name, input_json=LlmToolInputJson(input_json)
            )
        ],
    )


def knowledge_item(
    title: str,
    price_minor: int | None,
    currency_code: str,
    formatted_price: str | None = None,
) -> KnowledgeItemView:
    return KnowledgeItemView(
        id=KnowledgeItemId(),
        kind=KnowledgeItemKind.MENU_ITEM,
        title=KnowledgeTitle(title),
        price_minor=None if price_minor is None else MoneyAmountMinor(price_minor),
        currency_code=None if price_minor is None else CurrencyCode(currency_code),
        formatted_price=(
            None if formatted_price is None else FormattedMoneyText(formatted_price)
        ),
    )


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
) -> BrainWorld:
    clock = ManualClock()
    wall_clock: WallClock[Microseconds] = clock.wall_clock()
    owner_id, staff_id = UserId(), UserId()
    business_repo = BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
    profile_repo = BusinessProfileRepository(
        InMemoryDocumentCollectionAdapter[BusinessProfileDocument](
            BusinessProfileDocument
        )
    )
    exception_repo = ScheduleExceptionRepository(
        InMemoryDocumentCollectionAdapter[ScheduleExceptionDocument](
            ScheduleExceptionDocument
        )
    )
    version_repo = AssistantVersionRepository(
        InMemoryDocumentCollectionAdapter[AssistantVersionDocument](
            AssistantVersionDocument
        )
    )
    contact_repo = ContactRepository(
        InMemoryDocumentCollectionAdapter[ContactDocument](ContactDocument)
    )
    conversation_repo = ConversationRepository(
        InMemoryDocumentCollectionAdapter[ConversationDocument](ConversationDocument)
    )
    message_repo = MessageRepository(
        InMemoryDocumentCollectionAdapter[MessageDocument](MessageDocument)
    )
    llm_turn_repo = LlmTurnRepository(
        InMemoryDocumentCollectionAdapter[LlmTurnDocument](LlmTurnDocument)
    )
    usage_event_repo = UsageEventRepository(
        InMemoryDocumentCollectionAdapter[UsageEventDocument](UsageEventDocument)
    )
    channel_repo = ChannelRepository(InMemoryDocumentCollectionAdapter(ChannelDocument))
    call_repo = CallRepository(InMemoryDocumentCollectionAdapter(CallDocument))
    handoff_repo = HandoffRepository(
        InMemoryDocumentCollectionAdapter[HandoffDocument](HandoffDocument)
    )
    audit_log_repo = AuditLogRepository(
        InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](AuditLogEntryDocument)
    )
    user_repo = UserRepository(
        InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
    )
    knowledge_item_repo = KnowledgeItemRepository(
        InMemoryDocumentCollectionAdapter[KnowledgeItemDocument](KnowledgeItemDocument)
    )
    for user_id, phone in ((owner_id, "+995599000001"), (staff_id, "+995599000002")):
        user_repo.save(
            UserDocument(
                id=user_id,
                login_method=LoginMethod.PHONE,
                phone_number=E164PhoneNumber(phone),
                locale=LanguageTag("en"),
                is_verified=True,
            )
        )

    business = BusinessDocument(
        name=BusinessName(setup.name),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode(setup.country_code),
        timezone=TimezoneName(setup.timezone),
        currency_code=CurrencyCode(setup.currency_code),
        languages=[LanguageTag(tag) for tag in setup.languages],
        default_language=LanguageTag(setup.languages[0]),
        owner_language=LanguageTag(setup.languages[0]),
        plan_key=PlanKey.VOICE_AND_CHAT,
        status=setup.status,
        data_region=DataRegion.EU,
        members=[
            BusinessMember(user_id=owner_id, role=BusinessMemberRole.OWNER),
            BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF),
        ],
    )
    version = AssistantVersionDocument(
        business_id=business.id,
        version_number=AssistantVersionNumber(1),
        status=(
            AssistantVersionStatus.PUBLISHED
            if is_published
            else AssistantVersionStatus.READY
        ),
        niche_key=NicheKey.RESTAURANT,
        model_id=LlmModelId("scripted"),
        prompt_text=SystemPromptText(f"You are the AI assistant of {setup.name}."),
        tools=list(ALL_TOOLS if tools is None else tools),
        languages=[LanguageTag(tag) for tag in setup.languages],
        default_language=LanguageTag(setup.languages[0]),
        is_voice_enabled=True,
        facts=[
            BusinessFact(
                key=FactKey(key), label=FactLabel(label), value=FactValue(value)
            )
            for key, label, value in (
                facts
                if facts is not None
                else [
                    (
                        "signature_dish",
                        "Adjarian khachapuri",
                        f"18 {setup.currency_code}",
                    ),
                    ("opening_hours", "Opening hours", "Mon-Sun 12:00-23:00"),
                ]
            )
        ],
        profile_revision=Microseconds(0),
    )
    version_repo.save(version)
    if is_published:
        business.published_assistant_version_id = version.id

    business_repo.save(business)
    # The business's phone number, connected: the phone assistant is on.
    channel_repo.save(
        ChannelDocument(
            business_id=business.id,
            kind=ChannelKind.PHONE,
            external_id=ChannelExternalId("+995322000000"),
            status=ChannelStatus.CONNECTED,
        )
    )
    profile_repo.save(
        BusinessProfileDocument(
            business_id=business.id,
            niche_key=NicheKey.RESTAURANT,
            answers_language=LanguageTag(setup.languages[0]),
            hours=[
                OpeningInterval(
                    weekday=weekday,
                    opens_at=OpeningMinuteOfDay(opens),
                    closes_at=ClosingMinuteOfDay(closes),
                )
                for weekday in Weekday
                for opens, closes in (hours if hours is not None else [(720, 1380)])
            ],
        )
    )
    items: list[KnowledgeItemView] = (
        knowledge
        if knowledge is not None
        else [
            knowledge_item("Adjarian khachapuri", 1800, setup.currency_code, "18,00 ₾"),
            knowledge_item("Khinkali", 120, setup.currency_code),
            knowledge_item("Chef's surprise", None, setup.currency_code),
        ]
    )
    bookings = FakeBookings(timezone=business.timezone)
    search_knowledge = FakeSearchKnowledge(items)
    get_price = FakeGetPrice(items)
    availability = FakeCheckAvailability(business.timezone, ["19:30", "20:00"])
    create_lead = FakeCreateLead()
    handoff = FakeHandoff(handoff_repo, conversation_repo, wall_clock)
    record_question = FakeRecordUnansweredQuestion()
    texts = LocalizedTextResolver()
    run_tool = RunAssistantToolUseCase(
        search_knowledge=search_knowledge,
        get_price=get_price,
        send_link=FakeSendLink(
            {BusinessLinkKind.MENU: WebLink("https://sakhli.example/menu")}
        ),
        check_availability=availability,
        create_booking=FakeCreateBooking(bookings),
        cancel_booking=FakeCancelBooking(bookings),
        reschedule_booking=FakeRescheduleBooking(bookings),
        create_lead=create_lead,
        handoff_to_human=handoff,
        record_unanswered_question=record_question,
        phone_number_parser=PhoneNumberParser(),
    )
    storage_scope = StorageScopeContext()
    orchestrator = ConversationTurnOrchestrator(
        prepare_turn=PrepareConversationTurnUseCase(
            business_repo=business_repo,
            business_profile_repo=profile_repo,
            schedule_exception_repo=exception_repo,
            assistant_version_repo=version_repo,
            contact_repo=contact_repo,
            conversation_repo=conversation_repo,
            message_repo=message_repo,
            language_detector=LanguageDetector(),
            wall_clock=wall_clock,
            contact_message_limit=ContactMessageLimit(contact_message_limit),
        ),
        generate_reply=GenerateAssistantReplyUseCase(
            llm_adapter=llm,
            llm_turn_repo=llm_turn_repo,
            message_repo=message_repo,
            tool_registry=AssistantToolRegistry(),
            run_assistant_tool=run_tool,
            wall_clock=wall_clock,
            max_output_tokens=LlmMaxOutputTokens(4000),
            effort=LlmEffort.LOW,
            tool_round_limit=LlmToolRoundLimit(tool_round_limit),
        ),
        handoff_to_human=handoff,
        record_reply=RecordAssistantReplyUseCase(
            message_repo=message_repo,
            conversation_repo=conversation_repo,
            usage_event_repo=usage_event_repo,
            localized_text_resolver=texts,
            wall_clock=wall_clock,
        ),
        localized_text_resolver=texts,
        storage_scope=storage_scope,
    )
    voice_orchestrator = VoiceToolCallOrchestrator(
        open_voice_conversation=OpenVoiceConversationUseCase(
            business_repo=business_repo,
            assistant_version_repo=version_repo,
            contact_repo=contact_repo,
            conversation_repo=conversation_repo,
            channel_repo=channel_repo,
            plan_registry=PlanRegistry(),
            wall_clock=wall_clock,
        ),
        run_assistant_tool=run_tool,
        record_voice_tool_call=RecordVoiceToolCallUseCase(
            message_repo=message_repo,
            wall_clock=wall_clock,
        ),
        storage_scope=storage_scope,
    )
    return BrainWorld(
        clock=clock,
        owner_id=owner_id,
        staff_id=staff_id,
        business=business,
        version=version,
        llm=llm,
        business_repo=business_repo,
        profile_repo=profile_repo,
        exception_repo=exception_repo,
        version_repo=version_repo,
        contact_repo=contact_repo,
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        llm_turn_repo=llm_turn_repo,
        usage_event_repo=usage_event_repo,
        channel_repo=channel_repo,
        call_repo=call_repo,
        handoff_repo=handoff_repo,
        audit_log_repo=audit_log_repo,
        user_repo=user_repo,
        knowledge_item_repo=knowledge_item_repo,
        bookings=bookings,
        search_knowledge=search_knowledge,
        get_price=get_price,
        availability=availability,
        create_lead=create_lead,
        handoff=handoff,
        record_question=record_question,
        run_tool=run_tool,
        authorize=AuthorizeBusinessAccessUseCase(
            business_repo=business_repo,
            user_repo=user_repo,
            audit_log_repo=audit_log_repo,
            wall_clock=wall_clock,
        ),
        orchestrator=orchestrator,
        pipeline=CustomerMessagePipeline(orchestrator),
        voice_orchestrator=voice_orchestrator,
        greeting=BuildCallGreetingUseCase(
            business_repo=business_repo,
            localized_text_resolver=texts,
        ),
        texts=texts,
    )
