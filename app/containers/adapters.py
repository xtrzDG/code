from dependency_injector import containers
from dependency_injector.providers import Callable, DependenciesContainer, Singleton

from app.adapters.channels.instagram_channel_adapter import InstagramChannelAdapter
from app.adapters.channels.messenger_channel_adapter import MessengerChannelAdapter
from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.adapters.llm.menu_extraction_adapter import MenuExtractionAdapter
from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.adapters.llm.tracing_llm_adapter import TracingLlmAdapter
from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.adapters.recordings.local_recording_storage_adapter import (
    LocalRecordingStorageAdapter,
)
from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.adapters.storage.postgres.document_collection_factory import (
    build_document_collection,
)
from app.adapters.voice.elevenlabs_recording_storage_adapter import (
    ElevenLabsRecordingStorageAdapter,
)
from app.adapters.voice.elevenlabs_voice_agent_provisioner import (
    ElevenLabsVoiceAgentProvisioner,
)
from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.factories import (
    build_llm_trace_facilitator,
    resolve_recordings_directory,
    select_menu_extraction_model_id,
)
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.observability import LlmTraceFacilitatorContract
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
)
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.bookings import (
    BookingDocument,
    LeadDocument,
)
from app.schemas.domain.businesses import (
    BusinessDocument,
)
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.domain.channel_receipts import (
    ChannelMessageReceiptDocument,
)
from app.schemas.domain.channels import (
    ChannelDocument,
)
from app.schemas.domain.compliance import (
    AuditLogEntryDocument,
    DpaAcceptanceDocument,
)
from app.schemas.domain.contacts import (
    ContactDocument,
)
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import (
    HandoffDocument,
    UnansweredQuestionDocument,
)
from app.schemas.domain.jobs import (
    QueuedJobDocument,
)
from app.schemas.domain.knowledge import (
    KnowledgeItemDocument,
)
from app.schemas.domain.manager_links import (
    ManagerTelegramLinkDocument,
)
from app.schemas.domain.package_usage import (
    PackageUsageWarningDocument,
)
from app.schemas.domain.payments import (
    PaymentOrderDocument,
)
from app.schemas.domain.profiles import (
    BusinessProfileDocument,
)
from app.schemas.domain.resources import (
    ResourceDocument,
    ScheduleExceptionDocument,
)
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)


class AdaptersContainer(containers.DeclarativeContainer):
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Document collections: Postgres with DATABASE_URL, else in memory.
    # Names match app/utilities/storage/document_collection_catalog.py and
    # the tables created by migrations/.
    user_collection: Singleton[DocumentCollectionAdapterContract[UserDocument]] = (
        Singleton(
            build_document_collection,
            document_type=UserDocument,
            collection_name="users",
            settings=config.app_settings,
            connection_pool=clients.postgres_pool,
            storage_scope=utilities.storage_scope,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    otp_challenge_collection: Singleton[
        DocumentCollectionAdapterContract[OtpChallengeDocument]
    ] = Singleton(
        build_document_collection,
        document_type=OtpChallengeDocument,
        collection_name="otp_challenges",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    user_session_collection: Singleton[
        DocumentCollectionAdapterContract[UserSessionDocument]
    ] = Singleton(
        build_document_collection,
        document_type=UserSessionDocument,
        collection_name="user_sessions",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    business_collection: Singleton[
        DocumentCollectionAdapterContract[BusinessDocument]
    ] = Singleton(
        build_document_collection,
        document_type=BusinessDocument,
        collection_name="businesses",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    business_profile_collection: Singleton[
        DocumentCollectionAdapterContract[BusinessProfileDocument]
    ] = Singleton(
        build_document_collection,
        document_type=BusinessProfileDocument,
        collection_name="business_profiles",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    channel_collection: Singleton[
        DocumentCollectionAdapterContract[ChannelDocument]
    ] = Singleton(
        build_document_collection,
        document_type=ChannelDocument,
        collection_name="channels",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    knowledge_item_collection: Singleton[
        DocumentCollectionAdapterContract[KnowledgeItemDocument]
    ] = Singleton(
        build_document_collection,
        document_type=KnowledgeItemDocument,
        collection_name="knowledge_items",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resource_collection: Singleton[
        DocumentCollectionAdapterContract[ResourceDocument]
    ] = Singleton(
        build_document_collection,
        document_type=ResourceDocument,
        collection_name="resources",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    schedule_exception_collection: Singleton[
        DocumentCollectionAdapterContract[ScheduleExceptionDocument]
    ] = Singleton(
        build_document_collection,
        document_type=ScheduleExceptionDocument,
        collection_name="schedule_exceptions",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    contact_collection: Singleton[
        DocumentCollectionAdapterContract[ContactDocument]
    ] = Singleton(
        build_document_collection,
        document_type=ContactDocument,
        collection_name="contacts",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    conversation_collection: Singleton[
        DocumentCollectionAdapterContract[ConversationDocument]
    ] = Singleton(
        build_document_collection,
        document_type=ConversationDocument,
        collection_name="conversations",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    message_collection: Singleton[
        DocumentCollectionAdapterContract[MessageDocument]
    ] = Singleton(
        build_document_collection,
        document_type=MessageDocument,
        collection_name="messages",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    llm_turn_collection: Singleton[
        DocumentCollectionAdapterContract[LlmTurnDocument]
    ] = Singleton(
        build_document_collection,
        document_type=LlmTurnDocument,
        collection_name="llm_turns",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    call_collection: Singleton[DocumentCollectionAdapterContract[CallDocument]] = (
        Singleton(
            build_document_collection,
            document_type=CallDocument,
            collection_name="calls",
            settings=config.app_settings,
            connection_pool=clients.postgres_pool,
            storage_scope=utilities.storage_scope,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    booking_collection: Singleton[
        DocumentCollectionAdapterContract[BookingDocument]
    ] = Singleton(
        build_document_collection,
        document_type=BookingDocument,
        collection_name="bookings",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    lead_collection: Singleton[DocumentCollectionAdapterContract[LeadDocument]] = (
        Singleton(
            build_document_collection,
            document_type=LeadDocument,
            collection_name="leads",
            settings=config.app_settings,
            connection_pool=clients.postgres_pool,
            storage_scope=utilities.storage_scope,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    handoff_collection: Singleton[
        DocumentCollectionAdapterContract[HandoffDocument]
    ] = Singleton(
        build_document_collection,
        document_type=HandoffDocument,
        collection_name="handoffs",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    unanswered_question_collection: Singleton[
        DocumentCollectionAdapterContract[UnansweredQuestionDocument]
    ] = Singleton(
        build_document_collection,
        document_type=UnansweredQuestionDocument,
        collection_name="unanswered_questions",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    assistant_version_collection: Singleton[
        DocumentCollectionAdapterContract[AssistantVersionDocument]
    ] = Singleton(
        build_document_collection,
        document_type=AssistantVersionDocument,
        collection_name="assistant_versions",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    autotest_run_collection: Singleton[
        DocumentCollectionAdapterContract[AutotestRunDocument]
    ] = Singleton(
        build_document_collection,
        document_type=AutotestRunDocument,
        collection_name="autotest_runs",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    subscription_collection: Singleton[
        DocumentCollectionAdapterContract[SubscriptionDocument]
    ] = Singleton(
        build_document_collection,
        document_type=SubscriptionDocument,
        collection_name="subscriptions",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    invoice_collection: Singleton[
        DocumentCollectionAdapterContract[InvoiceDocument]
    ] = Singleton(
        build_document_collection,
        document_type=InvoiceDocument,
        collection_name="invoices",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    usage_event_collection: Singleton[
        DocumentCollectionAdapterContract[UsageEventDocument]
    ] = Singleton(
        build_document_collection,
        document_type=UsageEventDocument,
        collection_name="usage_events",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    audit_log_entry_collection: Singleton[
        DocumentCollectionAdapterContract[AuditLogEntryDocument]
    ] = Singleton(
        build_document_collection,
        document_type=AuditLogEntryDocument,
        collection_name="audit_log_entries",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    dpa_acceptance_collection: Singleton[
        DocumentCollectionAdapterContract[DpaAcceptanceDocument]
    ] = Singleton(
        build_document_collection,
        document_type=DpaAcceptanceDocument,
        collection_name="dpa_acceptances",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    queued_job_collection: Singleton[
        DocumentCollectionAdapterContract[QueuedJobDocument]
    ] = Singleton(
        build_document_collection,
        document_type=QueuedJobDocument,
        collection_name="queued_jobs",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    channel_message_receipt_collection: Singleton[
        DocumentCollectionAdapterContract[ChannelMessageReceiptDocument]
    ] = Singleton(
        build_document_collection,
        document_type=ChannelMessageReceiptDocument,
        collection_name="channel_message_receipts",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    manager_telegram_link_collection: Singleton[
        DocumentCollectionAdapterContract[ManagerTelegramLinkDocument]
    ] = Singleton(
        build_document_collection,
        document_type=ManagerTelegramLinkDocument,
        collection_name="manager_telegram_links",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    calendar_connection_collection: Singleton[
        DocumentCollectionAdapterContract[CalendarConnectionDocument]
    ] = Singleton(
        build_document_collection,
        document_type=CalendarConnectionDocument,
        collection_name="calendar_connections",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    calendar_authorization_state_collection: Singleton[
        DocumentCollectionAdapterContract[CalendarAuthorizationStateDocument]
    ] = Singleton(
        build_document_collection,
        document_type=CalendarAuthorizationStateDocument,
        collection_name="calendar_authorization_states",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    calendar_event_link_collection: Singleton[
        DocumentCollectionAdapterContract[CalendarEventLinkDocument]
    ] = Singleton(
        build_document_collection,
        document_type=CalendarEventLinkDocument,
        collection_name="calendar_event_links",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    payment_order_collection: Singleton[
        DocumentCollectionAdapterContract[PaymentOrderDocument]
    ] = Singleton(
        build_document_collection,
        document_type=PaymentOrderDocument,
        collection_name="payment_orders",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    package_usage_warning_collection: Singleton[
        DocumentCollectionAdapterContract[PackageUsageWarningDocument]
    ] = Singleton(
        build_document_collection,
        document_type=PackageUsageWarningDocument,
        collection_name="package_usage_warnings",
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Security and recordings.
    secret_cipher: Singleton[SecretCipherAdapter] = Singleton(
        SecretCipherAdapter,
        app_settings=config.app_settings,
    )
    local_recording_storage: Singleton[LocalRecordingStorageAdapter] = Singleton(
        LocalRecordingStorageAdapter,
        root_directory=Callable(
            resolve_recordings_directory,
            settings=config.app_settings,
        ),
    )
    # ElevenLabs keeps call audio in its own (EU) storage; other paths are
    # files of this server.
    recording_storage: Singleton[ElevenLabsRecordingStorageAdapter] = Singleton(
        ElevenLabsRecordingStorageAdapter,
        elevenlabs_client=clients.elevenlabs_client,
        fallback=local_recording_storage,
    )

    # --- Voice platform (ElevenLabs Agents).
    voice_webhook_adapter: Singleton[ElevenLabsVoiceWebhookAdapter] = Singleton(
        ElevenLabsVoiceWebhookAdapter,
        app_settings=config.app_settings,
    )
    voice_agent_provisioner: Singleton[ElevenLabsVoiceAgentProvisioner] = Singleton(
        ElevenLabsVoiceAgentProvisioner,
        elevenlabs_client=clients.elevenlabs_client,
        app_settings=config.app_settings,
    )

    # --- Messaging channels.
    telegram_channel_adapter: Singleton[TelegramChannelAdapter] = Singleton(
        TelegramChannelAdapter,
        telegram_client=clients.telegram_bot_client,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
    )
    # Also the WhatsApp template sender (staff notifications).
    whatsapp_channel_adapter: Singleton[WhatsAppChannelAdapter] = Singleton(
        WhatsAppChannelAdapter,
        meta_client=clients.meta_graph_client,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
    )
    messenger_channel_adapter: Singleton[MessengerChannelAdapter] = Singleton(
        MessengerChannelAdapter,
        meta_client=clients.meta_graph_client,
        app_settings=config.app_settings,
    )
    instagram_channel_adapter: Singleton[InstagramChannelAdapter] = Singleton(
        InstagramChannelAdapter,
        meta_client=clients.meta_graph_client,
        app_settings=config.app_settings,
    )

    # --- Language models.
    openai_llm_adapter: Singleton[OpenAiLlmAdapter] = Singleton(
        OpenAiLlmAdapter,
        client=clients.openai_responses_client,
    )
    anthropic_llm_adapter: Singleton[AnthropicLlmAdapter] = Singleton(
        AnthropicLlmAdapter,
        client=clients.anthropic_messages_client,
    )
    # Typed by its contract: tests replace it with the scripted model.
    routing_llm_adapter: Singleton[LlmAdapterContract] = Singleton(
        RoutingLlmAdapter,
        openai_adapter=openai_llm_adapter,
        anthropic_adapter=anthropic_llm_adapter,
    )
    # The quality journal (Langfuse, or nothing without keys). It lives here,
    # not in FacilitatorsContainer, because the LLM adapter below decorates
    # every model call with it and facilitators already depend on adapters.
    llm_trace_facilitator: Singleton[LlmTraceFacilitatorContract] = Singleton(
        build_llm_trace_facilitator,
        langfuse_client=clients.langfuse_ingestion_client,
    )
    # The adapter every use case gets: routing by model id, traced.
    llm_adapter: Singleton[TracingLlmAdapter] = Singleton(
        TracingLlmAdapter,
        inner_adapter=routing_llm_adapter,
        trace_facilitator=llm_trace_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
        monotonic_clock=time_provider.monotonic_clock,
        is_content_traced=config.app_settings.provided.is_llm_content_traced,
    )
    menu_extraction_adapter: Singleton[MenuExtractionAdapter] = Singleton(
        MenuExtractionAdapter,
        client=clients.openai_responses_client,
        model_id=Callable(
            select_menu_extraction_model_id,
            settings=config.app_settings,
        ),
    )

    # --- Payments.
    payment_gateway: Singleton[FlittPaymentGatewayAdapter] = Singleton(
        FlittPaymentGatewayAdapter,
        flitt_client=clients.flitt_client,
        app_base_url=config.app_settings.provided.app_base_url,
    )
