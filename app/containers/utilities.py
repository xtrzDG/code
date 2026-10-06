from dependency_injector import containers
from dependency_injector.providers import Callable, DependenciesContainer, Singleton
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import CollectorRegistry

from app.containers.config import ConfigContainer
from app.containers.telemetry_factories import is_sentry_tracing_enabled
from app.containers.time_provider import TimeProviderContainer
from app.contracts.health import ReadinessMemoryContract
from app.contracts.service_metrics import ServiceMetricsContract
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.storage import StorageScopeContract
from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.observability.metrics.metrics_exposition import (
    build_metrics_registry,
)
from app.utilities.observability.metrics.prometheus_service_metrics import (
    PrometheusServiceMetrics,
)
from app.utilities.observability.readiness_memory import ReadinessMemory
from app.utilities.observability.tracing.open_telemetry_setup import (
    build_tracer_provider,
)
from app.utilities.observability.tracing.span_tracer import SpanTracer
from app.utilities.observability.tracing.span_tracer_factory import build_span_tracer
from app.utilities.security.booking_manage_token_signer import (
    BookingManageTokenSigner,
)
from app.utilities.security.require_recent_authentication import (
    RequireRecentAuthentication,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from app.utilities.security.widget_stream_ticket_signer import (
    WidgetStreamTicketSigner,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext


class UtilitiesContainer(containers.DeclarativeContainer):
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    phone_number_parser: Singleton[PhoneNumberParser] = Singleton(PhoneNumberParser)
    localized_text_resolver: Singleton[LocalizedTextResolver] = Singleton(
        LocalizedTextResolver
    )
    language_detector: Singleton[LanguageDetector] = Singleton(LanguageDetector)
    # One scope shared by every Postgres collection of the process, and by
    # the operators, orchestrators and the worker that enter it.
    storage_scope: Singleton[StorageScopeContract] = Singleton(StorageScopeContext)
    # What GET /readyz remembers between probes of this process.
    readiness_memory: Singleton[ReadinessMemoryContract] = Singleton(ReadinessMemory)
    # The signed-in session of the request being served (bound by the HTTP
    # gateway), and the step-up check of every sensitive action.
    session_assurance: Singleton[SessionAssuranceContract] = Singleton(
        SessionAssuranceContext
    )
    step_up_guard: Singleton[StepUpGuardContract] = Singleton(
        RequireRecentAuthentication,
        session_assurance=session_assurance,
        wall_clock=time_provider.microsecond_wall_clock,
        max_age=config.app_settings.provided.step_up_max_age_seconds,
    )
    # Signed links of a guest's booking page (/r/{token}); the key derives
    # from ENCRYPTION_KEYS, one signer per process.
    booking_manage_token_signer: Singleton[BookingManageTokenSigner] = Singleton(
        BookingManageTokenSigner,
        encryption_key=config.app_settings.provided.encryption_key,
        previous_keys=config.app_settings.provided.previous_encryption_keys,
    )
    # Tickets of the website chat's live stream (the visitor key never goes
    # into its address); the key derives from ENCRYPTION_KEYS as well.
    widget_stream_ticket_signer: Singleton[WidgetStreamTicketSigner] = Singleton(
        WidgetStreamTicketSigner,
        encryption_key=config.app_settings.provided.encryption_key,
        previous_keys=config.app_settings.provided.previous_encryption_keys,
    )
    # This process's Prometheus series (GET /metrics, WORKER_METRICS_PORT)
    # and its spans: OpenTelemetry with OTEL_EXPORTER_OTLP_ENDPOINT, Sentry's
    # performance traces with SENTRY_DSN (docs/operations/observability.md).
    metrics_registry: Singleton[CollectorRegistry] = Singleton(
        build_metrics_registry,
        multiproc_directory=(
            config.app_settings.provided.telemetry.prometheus_multiproc_directory
        ),
    )
    service_metrics: Singleton[ServiceMetricsContract] = Singleton(
        PrometheusServiceMetrics, registry=metrics_registry
    )
    tracer_provider: Singleton[TracerProvider | None] = Singleton(
        build_tracer_provider,
        settings=config.app_settings.provided.telemetry,
        environment=config.app_settings.provided.environment,
        release=config.app_settings.provided.release_version,
    )
    span_tracer: Singleton[SpanTracer] = Singleton(
        build_span_tracer,
        tracer_provider=tracer_provider,
        is_sentry_tracing_enabled=Callable(
            is_sentry_tracing_enabled, settings=config.app_settings
        ),
    )
