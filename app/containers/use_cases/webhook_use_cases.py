from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

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
from app.facilitators.integrations.webhook_disabled_notice_facilitator import (
    WebhookDisabledNoticeFacilitator,
)
from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookAttempt,
    WebhookDeliveryJob,
)
from app.schemas.dto.integrations.webhook_views import (
    CreatedWebhookEndpoint,
    CreateWebhookEndpointCommand,
    UpdateWebhookEndpointCommand,
    WebhookDeliveriesQuery,
    WebhookDeliveryCommand,
    WebhookDeliveryDetail,
    WebhookDeliveryPage,
    WebhookDeliveryView,
    WebhookEndpointCommand,
    WebhookEndpointList,
    WebhookEndpointsQuery,
    WebhookEndpointView,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.integrations.attempt_webhook_delivery_use_case import (
    AttemptWebhookDeliveryUseCase,
)
from app.use_cases.integrations.create_webhook_endpoint_use_case import (
    CreateWebhookEndpointUseCase,
)
from app.use_cases.integrations.create_webhook_test_delivery_use_case import (
    CreateWebhookTestDeliveryUseCase,
)
from app.use_cases.integrations.delete_webhook_endpoint_use_case import (
    DeleteWebhookEndpointUseCase,
)
from app.use_cases.integrations.get_webhook_delivery_use_case import (
    GetWebhookDeliveryUseCase,
)
from app.use_cases.integrations.list_webhook_deliveries_use_case import (
    ListWebhookDeliveriesUseCase,
)
from app.use_cases.integrations.list_webhook_endpoints_use_case import (
    ListWebhookEndpointsUseCase,
)
from app.use_cases.integrations.purge_webhook_deliveries_use_case import (
    PurgeWebhookDeliveriesUseCase,
)
from app.use_cases.integrations.record_webhook_attempt_use_case import (
    RecordWebhookAttemptUseCase,
)
from app.use_cases.integrations.retry_webhook_delivery_use_case import (
    RetryWebhookDeliveryUseCase,
)
from app.use_cases.integrations.rotate_webhook_secret_use_case import (
    RotateWebhookSecretUseCase,
)
from app.use_cases.integrations.update_webhook_endpoint_use_case import (
    UpdateWebhookEndpointUseCase,
)


class WebhookUseCasesContainer(containers.DeclarativeContainer):
    """
    Outbound webhooks (1181): Settings → Integrations (endpoints, the
    delivery log, a test event, a retry), the `deliver_webhook` job's
    attempt and its recording, and the daily purge of the log.
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
    endpoints = repositories.webhook_endpoint_repo
    deliveries = repositories.webhook_delivery_repo
    failures_before_disable = (
        config.app_settings.provided.public_api.webhook_failures_before_disable
    )

    list_webhook_endpoints_use_case: Factory[
        UseCaseContract[WebhookEndpointsQuery, WebhookEndpointList]
    ] = Factory(
        ListWebhookEndpointsUseCase,
        authorize_business_access=authorize,
        endpoint_repo=endpoints,
        failures_before_disable=failures_before_disable,
    )
    create_webhook_endpoint_use_case: Factory[
        UseCaseContract[CreateWebhookEndpointCommand, CreatedWebhookEndpoint]
    ] = Factory(
        CreateWebhookEndpointUseCase,
        authorize_business_access=authorize,
        endpoint_repo=endpoints,
        poster=clients.webhook_poster,
        cipher=adapters.secret_cipher,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    update_webhook_endpoint_use_case: Factory[
        UseCaseContract[UpdateWebhookEndpointCommand, WebhookEndpointView]
    ] = Factory(
        UpdateWebhookEndpointUseCase,
        authorize_business_access=authorize,
        endpoint_repo=endpoints,
        poster=clients.webhook_poster,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    rotate_webhook_secret_use_case: Factory[
        UseCaseContract[WebhookEndpointCommand, CreatedWebhookEndpoint]
    ] = Factory(
        RotateWebhookSecretUseCase,
        authorize_business_access=authorize,
        endpoint_repo=endpoints,
        cipher=adapters.secret_cipher,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    delete_webhook_endpoint_use_case: Factory[
        UseCaseContract[WebhookEndpointCommand, None]
    ] = Factory(
        DeleteWebhookEndpointUseCase,
        authorize_business_access=authorize,
        endpoint_repo=endpoints,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    list_webhook_deliveries_use_case: Factory[
        UseCaseContract[WebhookDeliveriesQuery, WebhookDeliveryPage]
    ] = Factory(
        ListWebhookDeliveriesUseCase,
        authorize_business_access=authorize,
        endpoint_repo=endpoints,
        delivery_repo=deliveries,
    )
    get_webhook_delivery_use_case: Factory[
        UseCaseContract[WebhookDeliveryCommand, WebhookDeliveryDetail]
    ] = Factory(
        GetWebhookDeliveryUseCase,
        authorize_business_access=authorize,
        delivery_repo=deliveries,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    retry_webhook_delivery_use_case: Factory[
        UseCaseContract[WebhookDeliveryCommand, WebhookDeliveryView]
    ] = Factory(
        RetryWebhookDeliveryUseCase,
        authorize_business_access=authorize,
        delivery_repo=deliveries,
        rate_limits=registries.request_rate_limit_registry,
        job_queue=facilitators.job_queue_facilitator,
        unit_of_work=adapters.storage_unit_of_work,
        wall_clock=wall_clock,
    )
    create_webhook_test_delivery_use_case: Factory[
        UseCaseContract[WebhookEndpointCommand, WebhookDeliveryJob]
    ] = Factory(
        CreateWebhookTestDeliveryUseCase,
        authorize_business_access=authorize,
        endpoint_repo=endpoints,
        delivery_repo=deliveries,
        rate_limits=registries.request_rate_limit_registry,
        wall_clock=wall_clock,
    )
    attempt_webhook_delivery_use_case: Factory[
        UseCaseContract[WebhookDeliveryJob, WebhookAttempt | None]
    ] = Factory(
        AttemptWebhookDeliveryUseCase,
        delivery_repo=deliveries,
        endpoint_repo=endpoints,
        cipher=adapters.secret_cipher,
        poster=clients.webhook_poster,
        wall_clock=wall_clock,
    )
    # An endpoint switched off on its own: alert, audit entry, live event.
    webhook_disabled_notices: Singleton[WebhookDisabledNoticeFacilitator] = Singleton(
        WebhookDisabledNoticeFacilitator,
        business_repo=repositories.business_repo,
        staff_alerts=facilitators.staff_alert_facilitator,
        audit_log_repo=repositories.audit_log_repo,
        live_events=facilitators.event_publisher,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    record_webhook_attempt_use_case: Factory[
        UseCaseContract[WebhookAttempt, WebhookDeliveryDocument | None]
    ] = Factory(
        RecordWebhookAttemptUseCase,
        delivery_repo=deliveries,
        endpoint_repo=endpoints,
        job_queue=facilitators.job_queue_facilitator,
        unit_of_work=adapters.storage_unit_of_work,
        failures_before_disable=failures_before_disable,
        notices=webhook_disabled_notices,
    )
    # The daily `purge_webhook_deliveries` job.
    purge_webhook_deliveries_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            PurgeWebhookDeliveriesUseCase,
            delivery_repo=deliveries,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=wall_clock,
        )
    )
