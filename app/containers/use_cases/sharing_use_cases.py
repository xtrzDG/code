from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffCommand,
    WidgetHandoffNotice,
    WidgetHandoffTarget,
    WidgetHandoffView,
)
from app.schemas.dto.sharing import (
    HostedChatLookup,
    HostedChatView,
    PublicSlugCommand,
    ShareLinksQuery,
    ShareLinksView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.sharing.get_hosted_chat_use_case import GetHostedChatUseCase
from app.use_cases.sharing.get_share_links_use_case import GetShareLinksUseCase
from app.use_cases.sharing.resolve_hosted_chat_use_case import (
    ResolveHostedChatUseCase,
)
from app.use_cases.sharing.set_public_slug_use_case import SetPublicSlugUseCase
from app.use_cases.widget.open_widget_handoff_use_case import (
    OpenWidgetHandoffUseCase,
)
from app.use_cases.widget.record_widget_handoff_notice_use_case import (
    RecordWidgetHandoffNoticeUseCase,
)


class SharingUseCasesContainer(containers.DeclarativeContainer):
    """
    Reaching customers without a website: the share links and the hosted
    chat page's address (cabinet), the page's public configuration, and
    the website chat's "Talk to a person".
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_share_links_use_case: Factory[
        UseCaseContract[ShareLinksQuery, ShareLinksView]
    ] = Factory(
        GetShareLinksUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        business_profile_repo=repositories.business_profile_repo,
        public_slug_claim_repo=repositories.public_slug_claim_repo,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    set_public_slug_use_case: Factory[
        UseCaseContract[PublicSlugCommand, ShareLinksView]
    ] = Factory(
        SetPublicSlugUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        business_profile_repo=repositories.business_profile_repo,
        public_slug_claim_repo=repositories.public_slug_claim_repo,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resolve_hosted_chat_use_case: Factory[
        UseCaseContract[HostedChatLookup, BusinessId]
    ] = Factory(
        ResolveHostedChatUseCase,
        public_slug_claim_repo=repositories.public_slug_claim_repo,
        storage_scope=utilities.storage_scope,
    )
    get_hosted_chat_use_case: Factory[UseCaseContract[BusinessId, HostedChatView]] = (
        Factory(
            GetHostedChatUseCase,
            business_repo=repositories.business_repo,
            channel_repo=repositories.channel_repo,
            business_profile_repo=repositories.business_profile_repo,
            language_registry=registries.language_registry,
            app_settings=config.app_settings,
        )
    )
    open_widget_handoff_use_case: Factory[
        UseCaseContract[WidgetHandoffCommand, WidgetHandoffTarget]
    ] = Factory(
        OpenWidgetHandoffUseCase,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        text_resolver=utilities.localized_text_resolver,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_widget_handoff_notice_use_case: Factory[
        UseCaseContract[WidgetHandoffNotice, WidgetHandoffView]
    ] = Factory(
        RecordWidgetHandoffNoticeUseCase,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        language_registry=registries.language_registry,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
