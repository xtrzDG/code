from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.bookings import CreateLeadCommand
from app.schemas.dto.integrations.api_key_views import (
    ApiKeyCommand,
    ApiKeyList,
    ApiKeysQuery,
    CreateApiKeyCommand,
    CreatedApiKey,
)
from app.schemas.dto.integrations.webhook_views import CreatedWebhookEndpoint
from app.schemas.dto.operations.bookings import ManualBookingCommand
from app.schemas.dto.public_api.access import (
    ApiKeyCredentials,
    ApiKeyPrincipal,
    PublicApiCall,
    PublicApiIdentity,
    PublicBookingQuery,
    PublicContactQuery,
    PublicConversationQuery,
    PublicLeadQuery,
    PublicListQuery,
)
from app.schemas.dto.public_api.activity import PublicConversationDetail
from app.schemas.dto.public_api.commands import (
    PublicBookingCommand,
    PublicLeadCommand,
    PublicWebhookCommand,
    PublicWebhookRemoval,
)
from app.schemas.dto.public_api.pages import (
    PublicBookingPage,
    PublicContactPage,
    PublicConversationPage,
    PublicLeadPage,
)
from app.schemas.dto.public_api.records import PublicBooking, PublicContact, PublicLead
from app.use_cases.integrations.authenticate_api_key_use_case import (
    AuthenticateApiKeyUseCase,
)
from app.use_cases.integrations.create_api_key_use_case import CreateApiKeyUseCase
from app.use_cases.integrations.list_api_keys_use_case import ListApiKeysUseCase
from app.use_cases.integrations.public_api.public_bookings_use_cases import (
    GetPublicBookingUseCase,
    ListPublicBookingsUseCase,
)
from app.use_cases.integrations.public_api.public_contacts_use_cases import (
    GetPublicContactUseCase,
    ListPublicContactsUseCase,
)
from app.use_cases.integrations.public_api.public_conversations_use_cases import (
    GetPublicConversationUseCase,
    ListPublicConversationsUseCase,
)
from app.use_cases.integrations.public_api.public_identity_use_case import (
    GetPublicIdentityUseCase,
)
from app.use_cases.integrations.public_api.public_leads_use_cases import (
    GetPublicLeadUseCase,
    ListPublicLeadsUseCase,
)
from app.use_cases.integrations.public_api.public_webhook_subscriptions import (
    SubscribePublicWebhookUseCase,
    UnsubscribePublicWebhookUseCase,
)
from app.use_cases.integrations.public_api.start_public_booking_use_case import (
    StartPublicBookingUseCase,
)
from app.use_cases.integrations.public_api.start_public_lead_use_case import (
    StartPublicLeadUseCase,
)
from app.use_cases.integrations.revoke_api_key_use_case import RevokeApiKeyUseCase

type Reads[Query, Answer] = Factory[UseCaseContract[Query, Answer]]


class PublicApiUseCasesContainer(containers.DeclarativeContainer):
    """
    API keys (Settings → Integrations, owners) and the stable public API
    `/v1/public-api/*` they open: authentication with per-key limits, the
    reads of bookings, leads, contacts and conversations, the creating
    steps and Zapier's REST-hook subscriptions (1181).
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    authorize = account_use_cases.authorize_business_access_use_case
    wall_clock = time_provider.microsecond_wall_clock
    audit = repositories.audit_log_repo
    businesses = repositories.business_repo
    reader = facilitators.public_record_reader
    requests_per_minute = config.app_settings.provided.public_api.requests_per_minute

    list_api_keys_use_case: Reads[ApiKeysQuery, ApiKeyList] = Factory(
        ListApiKeysUseCase,
        authorize_business_access=authorize,
        api_key_repo=repositories.api_key_repo,
        requests_per_minute=requests_per_minute,
    )
    create_api_key_use_case: Reads[CreateApiKeyCommand, CreatedApiKey] = Factory(
        CreateApiKeyUseCase,
        authorize_business_access=authorize,
        api_key_repo=repositories.api_key_repo,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    revoke_api_key_use_case: Reads[ApiKeyCommand, None] = Factory(
        RevokeApiKeyUseCase,
        authorize_business_access=authorize,
        api_key_repo=repositories.api_key_repo,
        endpoint_repo=repositories.webhook_endpoint_repo,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    authenticate_api_key_use_case: Reads[ApiKeyCredentials, ApiKeyPrincipal] = Factory(
        AuthenticateApiKeyUseCase,
        api_key_repo=repositories.api_key_repo,
        business_repo=businesses,
        rate_limits=registries.request_rate_limit_registry,
        storage_scope=utilities.storage_scope,
        requests_per_minute=requests_per_minute,
        wall_clock=wall_clock,
    )
    get_public_identity_use_case: Reads[PublicApiCall, PublicApiIdentity] = Factory(
        GetPublicIdentityUseCase,
        business_repo=businesses,
        requests_per_minute=requests_per_minute,
    )
    list_public_bookings_use_case: Reads[PublicListQuery, PublicBookingPage] = Factory(
        ListPublicBookingsUseCase,
        business_repo=businesses,
        booking_repo=repositories.booking_repo,
        record_reader=reader,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    get_public_booking_use_case: Reads[PublicBookingQuery, PublicBooking] = Factory(
        GetPublicBookingUseCase,
        business_repo=businesses,
        record_reader=reader,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    describe_public_booking_use_case: Reads[PublicBookingQuery, PublicBooking] = (
        Factory(
            GetPublicBookingUseCase,
            business_repo=businesses,
            record_reader=reader,
            audit_log_repo=audit,
            wall_clock=wall_clock,
            is_audited=False,
        )
    )
    list_public_leads_use_case: Reads[PublicListQuery, PublicLeadPage] = Factory(
        ListPublicLeadsUseCase,
        business_repo=businesses,
        lead_repo=repositories.lead_repo,
        record_reader=reader,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    get_public_lead_use_case: Reads[PublicLeadQuery, PublicLead] = Factory(
        GetPublicLeadUseCase,
        business_repo=businesses,
        record_reader=reader,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    describe_public_lead_use_case: Reads[PublicLeadQuery, PublicLead] = Factory(
        GetPublicLeadUseCase,
        business_repo=businesses,
        record_reader=reader,
        audit_log_repo=audit,
        wall_clock=wall_clock,
        is_audited=False,
    )
    list_public_contacts_use_case: Reads[PublicListQuery, PublicContactPage] = Factory(
        ListPublicContactsUseCase,
        business_repo=businesses,
        contact_repo=repositories.contact_repo,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    get_public_contact_use_case: Reads[PublicContactQuery, PublicContact] = Factory(
        GetPublicContactUseCase,
        business_repo=businesses,
        record_reader=reader,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    list_public_conversations_use_case: Reads[
        PublicListQuery, PublicConversationPage
    ] = Factory(
        ListPublicConversationsUseCase,
        business_repo=businesses,
        conversation_repo=repositories.conversation_repo,
        record_reader=reader,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    get_public_conversation_use_case: Reads[
        PublicConversationQuery, PublicConversationDetail
    ] = Factory(
        GetPublicConversationUseCase,
        business_repo=businesses,
        record_reader=reader,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    start_public_booking_use_case: Reads[PublicBookingCommand, ManualBookingCommand] = (
        Factory(StartPublicBookingUseCase)
    )
    start_public_lead_use_case: Reads[PublicLeadCommand, CreateLeadCommand] = Factory(
        StartPublicLeadUseCase,
        business_repo=businesses,
        contact_repo=repositories.contact_repo,
        audit_log_repo=audit,
        phone_number_parser=utilities.phone_number_parser,
        wall_clock=wall_clock,
    )
    subscribe_public_webhook_use_case: Reads[
        PublicWebhookCommand, CreatedWebhookEndpoint
    ] = Factory(
        SubscribePublicWebhookUseCase,
        endpoint_repo=repositories.webhook_endpoint_repo,
        poster=clients.webhook_poster,
        cipher=adapters.secret_cipher,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
    unsubscribe_public_webhook_use_case: Reads[PublicWebhookRemoval, None] = Factory(
        UnsubscribePublicWebhookUseCase,
        endpoint_repo=repositories.webhook_endpoint_repo,
        audit_log_repo=audit,
        wall_clock=wall_clock,
    )
