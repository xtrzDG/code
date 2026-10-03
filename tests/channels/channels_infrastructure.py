"""The channels testbed's base: repositories, fakes, platform clients and adapters."""

from typed_time_provider import Microseconds, WallClock

from app.adapters.channels.instagram_channel_adapter import InstagramChannelAdapter
from app.adapters.channels.messenger_channel_adapter import MessengerChannelAdapter
from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.registries.localization.language_registry import LanguageRegistry
from app.repositories.assistant_repositories import AssistantVersionRepository
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
)
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.channel_repositories import ManagerTelegramLinkRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    CallRepository,
    ContactRepository,
    ConversationRepository,
    MessageRepository,
)
from app.repositories.delivery_repositories import (
    InboundEventRepository,
)
from app.repositories.knowledge_repositories import (
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.channels.channels_fakes import (
    AdjustableClock,
    FakeAuthenticationOperator,
    FakeCallGreetingUseCase,
    FakeSecretCipher,
    FakeVoiceToolCallOrchestrator,
)
from tests.channels.channels_settings import build_settings
from tests.channels.faulty_outbox import FaultyOutboundMessageRepository
from tests.channels.recording_transport import RecordingTransport
from tests.channels.scripted_customer_pipeline import ScriptedCustomerPipeline
from tests.live_events.recording_event_publisher import RecordingEventPublisher
from tests.platform.worker_fakes import JobStores, build_job_stores


class ChannelsInfrastructure:
    """In-memory repositories, fakes and real platform clients over mock transports."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings: AppSettings = settings or build_settings()
        self.clock: AdjustableClock = AdjustableClock()
        self.wall_clock: WallClock[Microseconds] = self.clock.build_wall_clock()
        # What the use cases announce to open cabinets.
        self.live_events: RecordingEventPublisher = RecordingEventPublisher()
        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter(BusinessDocument)
        )
        self.user_repo = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
        self.channel_repo = ChannelRepository(
            InMemoryDocumentCollectionAdapter(ChannelDocument)
        )
        self.contact_repo = ContactRepository(
            InMemoryDocumentCollectionAdapter(ContactDocument)
        )
        self.conversation_repo = ConversationRepository(
            InMemoryDocumentCollectionAdapter(ConversationDocument)
        )
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter(MessageDocument)
        )
        self.call_repo = CallRepository(InMemoryDocumentCollectionAdapter(CallDocument))
        self.booking_repo = BookingRepository(
            InMemoryDocumentCollectionAdapter(BookingDocument)
        )
        self.lead_repo = LeadRepository(InMemoryDocumentCollectionAdapter(LeadDocument))
        self.handoff_repo = HandoffRepository(
            InMemoryDocumentCollectionAdapter(HandoffDocument)
        )
        self.usage_event_repo = UsageEventRepository(
            InMemoryDocumentCollectionAdapter(UsageEventDocument)
        )
        self.audit_log_repo = AuditLogRepository(
            InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
        )
        self.profile_repo = BusinessProfileRepository(
            InMemoryDocumentCollectionAdapter(BusinessProfileDocument)
        )
        self.exception_repo = ScheduleExceptionRepository(
            InMemoryDocumentCollectionAdapter(ScheduleExceptionDocument)
        )
        self.resource_repo = ResourceRepository(
            InMemoryDocumentCollectionAdapter(ResourceDocument)
        )
        self.assistant_version_repo = AssistantVersionRepository(
            InMemoryDocumentCollectionAdapter(AssistantVersionDocument)
        )
        self.inbound_event_collection = InMemoryDocumentCollectionAdapter(
            InboundEventDocument
        )
        self.outbound_message_collection = InMemoryDocumentCollectionAdapter(
            OutboundMessageDocument
        )
        self.inbound_event_repo = InboundEventRepository(self.inbound_event_collection)
        self.outbound_message_repo = FaultyOutboundMessageRepository(
            self.outbound_message_collection
        )
        self.jobs: JobStores = build_job_stores()
        self.job_queue = JobQueueFacilitator(
            self.jobs.job_repo, self.wall_clock, self.jobs.job_wakeup
        )
        self.link_repo = ManagerTelegramLinkRepository(
            InMemoryDocumentCollectionAdapter(ManagerTelegramLinkDocument)
        )

        self.secret_cipher = FakeSecretCipher()
        self.widget_rate_limits = RequestRateLimitRegistry(
            InMemoryRateLimitBucketAdapter()
        )
        self.phone_number_parser = PhoneNumberParser()
        self.language_registry = LanguageRegistry()
        self.text_resolver = LocalizedTextResolver()
        self.pipeline = ScriptedCustomerPipeline(
            self.conversation_repo, self.message_repo, self.clock
        )
        self.voice_tool_orchestrator = FakeVoiceToolCallOrchestrator()
        self.call_greeting = FakeCallGreetingUseCase(self.business_repo)
        self.authentication = FakeAuthenticationOperator()

        self.telegram_transport = RecordingTransport()
        self.meta_transport = RecordingTransport()
        self.elevenlabs_transport = RecordingTransport()
        self.telegram_client = TelegramBotClient(
            transport=self.telegram_transport.build()
        )
        self.meta_client = MetaGraphClient(transport=self.meta_transport.build())
        self.elevenlabs_client = ElevenLabsClient(
            api_key=PlatformSecret("elevenlabs-api-key"),
            base_url=self.settings.elevenlabs_api_base_url,
            transport=self.elevenlabs_transport.build(),
        )

        self.telegram_adapter = TelegramChannelAdapter(
            self.telegram_client, self.phone_number_parser, self.settings
        )
        self.whatsapp_adapter = WhatsAppChannelAdapter(
            self.meta_client, self.phone_number_parser, self.settings
        )
        self.messenger_adapter = MessengerChannelAdapter(
            self.meta_client, self.settings
        )
        self.instagram_adapter = InstagramChannelAdapter(
            self.meta_client, self.settings
        )
        self.voice_webhook_adapter = ElevenLabsVoiceWebhookAdapter(self.settings)
