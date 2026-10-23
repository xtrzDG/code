from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.channels.channel_webhooks import MetaWebhookRequest
from app.schemas.dto.channels.comment_replies import SetInstagramCommentRepliesCommand
from app.schemas.dto.channels.meta_connection import (
    CompleteWhatsAppSignupCommand,
    ConnectMetaPageCommand,
    ListMetaPagesCommand,
    MetaConnectionStartView,
    MetaPageList,
    MetaSignInOptionsQuery,
    MetaSignInOptionsView,
    StartMetaConnectionCommand,
)
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboxIntake
from app.use_cases.channels.comment_replies.accept_instagram_comments_use_case import (
    AcceptInstagramCommentsUseCase,
)
from app.use_cases.channels.comment_replies.reply_to_comment_trigger_use_case import (
    ReplyToCommentTriggerUseCase,
)
from app.use_cases.channels.comment_replies.set_instagram_comment_replies_use_case import (  # noqa: E501
    SetInstagramCommentRepliesUseCase,
)
from app.use_cases.channels.meta_connection.complete_whatsapp_embedded_signup_use_case import (  # noqa: E501
    CompleteWhatsAppEmbeddedSignupUseCase,
)
from app.use_cases.channels.meta_connection.connect_meta_page_use_case import (
    ConnectMetaPageUseCase,
)
from app.use_cases.channels.meta_connection.get_meta_sign_in_options_use_case import (
    GetMetaSignInOptionsUseCase,
)
from app.use_cases.channels.meta_connection.list_meta_pages_use_case import (
    ListMetaPagesUseCase,
)
from app.use_cases.channels.meta_connection.start_meta_connection_use_case import (
    StartMetaConnectionUseCase,
)


class MetaConnectionUseCasesContainer(containers.DeclarativeContainer):
    """
    Meta's self-serve connection (R15, migration 1212): the Facebook
    sign-ins of the Channels page (WhatsApp Embedded Signup, the page
    picker of Messenger and Instagram) and Instagram comment-to-DM (its
    settings, the comments webhook's intake and the worker's private
    reply).
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

    get_meta_sign_in_options_use_case: Factory[
        UseCaseContract[MetaSignInOptionsQuery, MetaSignInOptionsView]
    ] = Factory(
        GetMetaSignInOptionsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        app_settings=config.app_settings,
    )
    start_meta_connection_use_case: Factory[
        UseCaseContract[StartMetaConnectionCommand, MetaConnectionStartView]
    ] = Factory(
        StartMetaConnectionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        state_repo=repositories.meta_connection_state_repo,
        step_up=utilities.step_up_guard,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    complete_whatsapp_signup_use_case: Factory[
        UseCaseContract[CompleteWhatsAppSignupCommand, ChannelView]
    ] = Factory(
        CompleteWhatsAppEmbeddedSignupUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        state_repo=repositories.meta_connection_state_repo,
        oauth_client=clients.meta_oauth_client,
        onboarding_client=clients.whatsapp_onboarding_client,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        audit_log_repo=repositories.audit_log_repo,
        product_events=facilitators.product_events,
        storage_scope=utilities.storage_scope,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_meta_pages_use_case: Factory[
        UseCaseContract[ListMetaPagesCommand, MetaPageList]
    ] = Factory(
        ListMetaPagesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        state_repo=repositories.meta_connection_state_repo,
        oauth_client=clients.meta_oauth_client,
        pages_client=clients.meta_pages_client,
        secret_cipher=adapters.secret_cipher,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    connect_meta_page_use_case: Factory[
        UseCaseContract[ConnectMetaPageCommand, ChannelView]
    ] = Factory(
        ConnectMetaPageUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        state_repo=repositories.meta_connection_state_repo,
        oauth_client=clients.meta_oauth_client,
        pages_client=clients.meta_pages_client,
        meta_client=clients.meta_graph_client,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        audit_log_repo=repositories.audit_log_repo,
        product_events=facilitators.product_events,
        storage_scope=utilities.storage_scope,
        step_up=utilities.step_up_guard,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    set_comment_replies_use_case: Factory[
        UseCaseContract[SetInstagramCommentRepliesCommand, ChannelView]
    ] = Factory(
        SetInstagramCommentRepliesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    accept_instagram_comments_use_case: Factory[
        UseCaseContract[MetaWebhookRequest, InboxIntake]
    ] = Factory(
        AcceptInstagramCommentsUseCase,
        channel_repo=repositories.channel_repo,
        instagram_adapter=adapters.instagram_channel_adapter,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
        unit_of_work=adapters.storage_unit_of_work,
    )
    reply_to_comment_trigger_use_case: Factory[
        UseCaseContract[InboundEventClaim, InboundAnswer]
    ] = Factory(
        ReplyToCommentTriggerUseCase,
        channel_repo=repositories.channel_repo,
        contact_repo=repositories.contact_repo,
        suppression_list=facilitators.suppression_list,
        outbound_message_repo=repositories.outbound_message_repo,
        job_queue=facilitators.job_queue_facilitator,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        unit_of_work=adapters.storage_unit_of_work,
    )
