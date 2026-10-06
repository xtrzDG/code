from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.channel_settings import (
    ChannelListQuery,
    ChannelView,
    ConnectChannelCommand,
    DisableChannelCommand,
)
from app.schemas.dto.channels.channel_webhooks import (
    MetaWebhookRequest,
    MetaWebhookVerificationRequest,
    TelegramWebhookRequest,
)
from app.schemas.dto.channels.provider_profiles import TelegramBotProfile
from app.schemas.dto.channels.staff_links import (
    CreateTelegramLinkCommand,
    PlatformBotUpdate,
    PlatformBotWebhookOutcome,
    PlatformBotWebhookSetup,
    TelegramLinkView,
)
from app.schemas.dto.channels.telegram_token_checks import (
    TelegramBotCheckView,
    ValidateTelegramTokenCommand,
)
from app.schemas.dto.channels.widget import (
    WidgetConfigView,
    WidgetMessageCommand,
    WidgetMessagesQuery,
    WidgetMessagesView,
    WidgetSnippetQuery,
    WidgetSnippetView,
)
from app.schemas.dto.channels.widget_streams import WidgetStreamTicketRequest
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.deliveries import RoutedInboundMessage
from app.schemas.dto.staff_reply_templates import (
    SetWhatsAppStaffTemplateCommand,
    SetWhatsAppStaffTemplatesCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.schemas.typings.channels.strings import MetaWebhookChallenge
from app.use_cases.channels.accept_widget_message_use_case import (
    AcceptWidgetMessageUseCase,
)
from app.use_cases.channels.configure_platform_bot_webhook_use_case import (
    ConfigurePlatformBotWebhookUseCase,
)
from app.use_cases.channels.connection.connect_channel_use_case import (
    ConnectChannelUseCase,
)
from app.use_cases.channels.connection.validate_telegram_token_use_case import (
    ValidateTelegramTokenUseCase,
)
from app.use_cases.channels.create_telegram_link_use_case import (
    CreateTelegramLinkUseCase,
)
from app.use_cases.channels.disable_channel_use_case import DisableChannelUseCase
from app.use_cases.channels.get_widget_config_use_case import GetWidgetConfigUseCase
from app.use_cases.channels.get_widget_messages_use_case import GetWidgetMessagesUseCase
from app.use_cases.channels.get_widget_snippet_use_case import GetWidgetSnippetUseCase
from app.use_cases.channels.handle_platform_bot_update_use_case import (
    HandlePlatformBotUpdateUseCase,
)
from app.use_cases.channels.list_channels_use_case import ListChannelsUseCase
from app.use_cases.channels.receive_meta_webhook_use_case import (
    ReceiveMetaWebhookUseCase,
)
from app.use_cases.channels.receive_telegram_webhook_use_case import (
    ReceiveTelegramWebhookUseCase,
)
from app.use_cases.channels.set_whatsapp_staff_template_use_case import (
    SetWhatsAppStaffTemplateUseCase,
)
from app.use_cases.channels.set_whatsapp_staff_templates_use_case import (
    SetWhatsAppStaffTemplatesUseCase,
)
from app.use_cases.channels.verify_meta_webhook_use_case import VerifyMetaWebhookUseCase
from app.use_cases.channels.widget_stream.issue_widget_stream_ticket_use_case import (
    IssueWidgetStreamTicketUseCase,
)


class ChannelUseCasesContainer(containers.DeclarativeContainer):
    """
    Messaging channels: webhooks and replies, cabinet channel settings, the
    website widget, staff links and the platform bot.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    voice_use_cases: VoiceUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    receive_telegram_webhook_use_case: Factory[
        UseCaseContract[TelegramWebhookRequest, list[RoutedInboundMessage]]
    ] = Factory(
        ReceiveTelegramWebhookUseCase,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        telegram_adapter=adapters.telegram_channel_adapter,
    )
    receive_meta_webhook_use_case: Factory[
        UseCaseContract[MetaWebhookRequest, list[RoutedInboundMessage]]
    ] = Factory(
        ReceiveMetaWebhookUseCase,
        channel_repo=repositories.channel_repo,
        whatsapp_adapter=adapters.whatsapp_channel_adapter,
        messenger_adapter=adapters.messenger_channel_adapter,
        instagram_adapter=adapters.instagram_channel_adapter,
    )
    verify_meta_webhook_use_case: Factory[
        UseCaseContract[MetaWebhookVerificationRequest, MetaWebhookChallenge]
    ] = Factory(
        VerifyMetaWebhookUseCase,
        app_settings=config.app_settings,
    )
    connect_channel_use_case: Factory[
        UseCaseContract[ConnectChannelCommand, ChannelView]
    ] = Factory(
        ConnectChannelUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        telegram_client=clients.telegram_bot_client,
        meta_client=clients.meta_graph_client,
        phone_number_parser=utilities.phone_number_parser,
        audit_log_repo=repositories.audit_log_repo,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        storage_scope=utilities.storage_scope,
        product_events=facilitators.product_events,
        step_up=utilities.step_up_guard,
    )
    set_whatsapp_staff_template_use_case: Factory[
        UseCaseContract[SetWhatsAppStaffTemplateCommand, ChannelView]
    ] = Factory(
        SetWhatsAppStaffTemplateUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    set_whatsapp_staff_templates_use_case: Factory[
        UseCaseContract[SetWhatsAppStaffTemplatesCommand, ChannelView]
    ] = Factory(
        SetWhatsAppStaffTemplatesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    validate_telegram_token_use_case: Factory[
        UseCaseContract[ValidateTelegramTokenCommand, TelegramBotCheckView]
    ] = Factory(
        ValidateTelegramTokenUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        telegram_client=clients.telegram_bot_client,
        telegram_file_client=clients.telegram_file_client,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    disable_channel_use_case: Factory[
        UseCaseContract[DisableChannelCommand, ChannelView]
    ] = Factory(
        DisableChannelUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        telegram_client=clients.telegram_bot_client,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        remove_voice_agent=voice_use_cases.remove_voice_agent_use_case,
    )
    list_channels_use_case: Factory[
        UseCaseContract[ChannelListQuery, list[ChannelView]]
    ] = Factory(
        ListChannelsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
    )
    get_widget_config_use_case: Factory[
        UseCaseContract[BusinessId, WidgetConfigView]
    ] = Factory(
        GetWidgetConfigUseCase,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        language_registry=registries.language_registry,
        language_detector=utilities.language_detector,
        app_settings=config.app_settings,
        referral_links=facilitators.referral_links,
    )
    # Singleton: it remembers the web chats it found open (OpenChatMemory).
    get_widget_messages_use_case: Singleton[
        UseCaseContract[WidgetMessagesQuery, WidgetMessagesView]
    ] = Singleton(
        GetWidgetMessagesUseCase,
        channel_repo=repositories.channel_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        language_registry=registries.language_registry,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        read_session=adapters.storage_read_session,
    )
    # A ticket to the visitor's live stream with each widget answer.
    issue_widget_stream_ticket_use_case: Factory[
        UseCaseContract[WidgetStreamTicketRequest, WidgetStreamTicket]
    ] = Factory(
        IssueWidgetStreamTicketUseCase,
        ticket_signer=utilities.widget_stream_ticket_signer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    accept_widget_message_use_case: Factory[
        UseCaseContract[WidgetMessageCommand, InboundMessage]
    ] = Factory(
        AcceptWidgetMessageUseCase,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_widget_snippet_use_case: Factory[
        UseCaseContract[WidgetSnippetQuery, WidgetSnippetView]
    ] = Factory(
        GetWidgetSnippetUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        app_settings=config.app_settings,
    )
    # Singleton: it caches the platform bot's username.
    create_telegram_link_use_case: Singleton[
        UseCaseContract[CreateTelegramLinkCommand, TelegramLinkView]
    ] = Singleton(
        CreateTelegramLinkUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        link_repo=repositories.manager_telegram_link_repo,
        language_registry=registries.language_registry,
        telegram_client=clients.telegram_bot_client,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    handle_platform_bot_update_use_case: Factory[
        UseCaseContract[PlatformBotUpdate, PlatformBotWebhookOutcome]
    ] = Factory(
        HandlePlatformBotUpdateUseCase,
        link_repo=repositories.manager_telegram_link_repo,
        business_repo=repositories.business_repo,
        audit_log_repo=repositories.audit_log_repo,
        telegram_client=clients.telegram_bot_client,
        text_resolver=utilities.localized_text_resolver,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    configure_platform_bot_webhook_use_case: Factory[
        UseCaseContract[PlatformBotWebhookSetup, TelegramBotProfile]
    ] = Factory(
        ConfigurePlatformBotWebhookUseCase,
        telegram_client=clients.telegram_bot_client,
        app_settings=config.app_settings,
    )
