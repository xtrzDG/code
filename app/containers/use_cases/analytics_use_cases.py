from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.billing_use_cases import BillingUseCasesContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.analytics.admin_metrics_query import AdminMetricsQuery
from app.schemas.dto.analytics.admin_metrics_view import AdminMetricsView
from app.schemas.dto.analytics.telemetry import (
    TelemetryBatchCommand,
    TelemetryBatchReceipt,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.admin.metrics.get_admin_metrics_use_case import (
    GetAdminMetricsUseCase,
)
from app.use_cases.admin.metrics.reconcile_product_events_use_case import (
    ReconcileProductEventsUseCase,
)
from app.use_cases.telemetry.purge_web_vitals_use_case import PurgeWebVitalsUseCase
from app.use_cases.telemetry.record_telemetry_use_case import RecordTelemetryUseCase


class AnalyticsUseCasesContainer(containers.DeclarativeContainer):
    """
    The founder's growth analytics: the admin metrics, the cabinet's
    telemetry, the daily purge of Web Vitals and the daily reconciliation
    of the product events with the stored records.
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    billing_use_cases: BillingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_admin_metrics_use_case: Factory[
        UseCaseContract[AdminMetricsQuery, AdminMetricsView]
    ] = Factory(
        GetAdminMetricsUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        user_repo=repositories.user_repo,
        business_repo=repositories.business_repo,
        product_event_repo=repositories.product_event_repo,
        web_vital_sample_repo=repositories.web_vital_sample_repo,
        compute_client_cost=billing_use_cases.compute_client_cost_use_case,
        exchange_rate_registry=registries.exchange_rate_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_telemetry_use_case: Factory[
        UseCaseContract[TelemetryBatchCommand, TelemetryBatchReceipt]
    ] = Factory(
        RecordTelemetryUseCase,
        web_vital_sample_repo=repositories.web_vital_sample_repo,
        business_repo=repositories.business_repo,
        product_events=facilitators.product_events,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    purge_web_vitals_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        PurgeWebVitalsUseCase,
        web_vital_sample_repo=repositories.web_vital_sample_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    reconcile_product_events_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            ReconcileProductEventsUseCase,
            user_repo=repositories.user_repo,
            business_repo=repositories.business_repo,
            activation_event_repo=repositories.activation_event_repo,
            channel_repo=repositories.channel_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            product_event_repo=repositories.product_event_repo,
            product_events=facilitators.product_events,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
