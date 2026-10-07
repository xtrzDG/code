"""
HTTP entry point (uvicorn factory):

    uv run uvicorn app.main:create_application --factory
"""

import logging
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import anyio.to_thread
from fastapi import FastAPI
from starlette.types import Lifespan

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.containers.app import AppContainer
from app.contracts.live_events import LiveEventBusAdapterContract
from app.contracts.observability import LlmTraceFacilitatorContract
from app.gateways.http import pipeline_watchdog_thread as watchdog
from app.gateways.http.access_log_redaction import install_access_log_redaction
from app.gateways.http.application import build_http_application
from app.gateways.http.background_threads import (
    EMBEDDED_WORKER_THREAD_NAME,
    TRACE_FLUSH_INTERVAL_SECONDS,
    start_embedded_worker,
    start_trace_flushing,
    stop_embedded_worker,
)
from app.gateways.http.live_events.exit_signals import end_streams_on_exit_signals
from app.gateways.http.metrics_routes import build_metrics_router
from app.gateways.http.router_assembly import build_application_routers
from app.gateways.http.spend_guard_router_assembly import (
    anonymous_request_admission_of,
)
from app.gateways.metrics.metrics_rendering import metrics_renderer
from app.gateways.startup_checks import check_processor_uses
from app.gateways.telemetry_lifecycle import (
    API_SERVICE_NAME,
    finish_telemetry,
    name_service,
    start_telemetry,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.dto.channels.provider_profiles import TelegramBotProfile
from app.schemas.dto.channels.staff_links import PlatformBotWebhookSetup
from app.schemas.dto.demo_data import DemoDataSeedReport, SeedDemoDataCommand
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.cldr_language_names import ENGLISH_LOCALE_IDENTIFIER
from app.utilities.observability.logging_setup import configure_logging

__all__ = [
    "EMBEDDED_WORKER_THREAD_NAME",
    "build_application",
    "check_dpa_document",
    "create_application",
    "report_login_code_channels",
]

LOGGER: logging.Logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """
    The API with settings from the environment (uvicorn factory). Log lines
    of the application and of uvicorn go out in LOG_FORMAT with their
    request, business and job.
    """

    install_access_log_redaction()
    name_service(API_SERVICE_NAME)
    app_container = AppContainer()
    configure_logging(app_container.config.app_settings().log_format)
    start_telemetry(app_container, is_api=True)
    return build_application(app_container)


def build_application(app_container: AppContainer) -> FastAPI:
    """The API over a ready container (tests pass one with overrides)."""

    settings: AppSettings = app_container.config.app_settings()
    return build_http_application(
        routers=[
            *build_application_routers(app_container),
            build_metrics_router(
                settings.telemetry.metrics_token, metrics_renderer(app_container)
            ),
        ],
        error_reporter=app_container.facilitators.error_reporter(),
        cors_allowed_origins=settings.cors_allowed_origins,
        lifespan=build_lifespan(app_container),
        environment=settings.environment,
        anonymous_request_admission=anonymous_request_admission_of(
            app_container.operators
        ),
        service_metrics=app_container.utilities.service_metrics(),
        span_tracer=app_container.utilities.span_tracer(),
        api_availability=app_container.gateways.api_availability_tally(),
    )


def build_lifespan(app_container: AppContainer) -> Lifespan[FastAPI]:
    """
    Startup: size the request threads (THREADPOOL_SIZE), warm the country
    catalog, check the DPA text and the sub-processor list, report the login
    code channels, seed the demo businesses (SEED_DEMO_DATA, once), point
    the platform bot at this API, start the trace flush, the pipeline
    watchdog and (EMBEDDED_WORKER) the worker; live streams end as soon as
    the process is asked to stop. Shutdown: stop the worker (running jobs
    may finish) and the watchdog, flush traces and spans, close the live
    event bus and the Postgres pool.
    """

    @asynccontextmanager
    async def lifespan(http_application: FastAPI) -> AsyncGenerator[None]:
        del http_application
        set_request_thread_limit(app_container)
        app_container.registries.country_registry().list_all()
        check_dpa_document(app_container)
        check_processor_uses(app_container)
        report_login_code_channels(app_container)
        seed_demo_data(app_container)
        configure_platform_bot(app_container)
        trace_facilitator: LlmTraceFacilitatorContract = (
            app_container.adapters.llm_trace_facilitator()
        )
        live_event_bus: LiveEventBusAdapterContract = (
            app_container.adapters.live_event_bus()
        )
        end_streams_on_exit_signals(live_event_bus.close)
        stop_event = threading.Event()
        flush_thread = start_trace_flushing(trace_facilitator, stop_event)
        watchdog_thread = watchdog.start_pipeline_watchdog(app_container, stop_event)
        worker_thread: threading.Thread | None = None
        try:
            worker_thread = start_embedded_worker(app_container, stop_event)
            yield
        finally:
            stop_event.set()
            if worker_thread is not None:
                stop_embedded_worker(worker_thread)
            watchdog.stop_pipeline_watchdog(watchdog_thread)
            flush_thread.join(timeout=TRACE_FLUSH_INTERVAL_SECONDS)
            trace_facilitator.flush()
            finish_telemetry(app_container)
            live_event_bus.close()
            close_postgres_pool(app_container)

    return lifespan


def set_request_thread_limit(app_container: AppContainer) -> None:
    """
    Sync request handlers run in AnyIO's worker threads, at most
    THREADPOOL_SIZE at once (AnyIO's default is 40); the Postgres pool
    (DB_POOL_SIZE) has as many connections by default, so a handler never
    waits for a connection another handler's thread holds.
    """

    settings: AppSettings = app_container.config.app_settings()
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = int(settings.threadpool_size)
    LOGGER.info(
        "Request threads: %d; database connections: %d",
        int(settings.threadpool_size),
        int(settings.db_pool_size),
    )


def check_dpa_document(app_container: AppContainer) -> None:
    """
    The configured data processing agreement must have its text in this
    build: owners cannot accept a version without one, and no business could
    go live. The texts are built into the image (docs/legal), so a new
    DPA_DOCUMENT_VERSION deployed onto an older build is refused in
    production at startup (the previous deploy keeps serving) and logged as
    a warning elsewhere.
    """

    settings: AppSettings = app_container.config.app_settings()
    version: DpaDocumentVersion = settings.dpa_document_version
    if (
        app_container.registries.legal_document_registry().find_dpa(
            version,
            LanguageTag(ENGLISH_LOCALE_IDENTIFIER),
        )
        is not None
    ):
        return

    message: str = (
        f"DPA_DOCUMENT_VERSION is {version}, but this build has no "
        f"docs/legal/dpa-{version}.<language>.md, so owners cannot accept it. "
        "Rebuild from the commit with the texts (Render: Manual Deploy -> "
        '"Deploy latest commit", or "Save, rebuild, and deploy").'
    )
    if settings.environment is DeploymentEnvironment.PRODUCTION:
        raise ValidationFailedError(message)

    LOGGER.warning(message)


def report_login_code_channels(app_container: AppContainer) -> None:
    """
    Log which channels can carry login codes. In production without any
    provider nobody can sign in, so that is logged as an error (each sign-in
    attempt then fails with HTTP 502 and the same explanation).
    """

    settings: AppSettings = app_container.config.app_settings()
    channels: frozenset[OtpDeliveryChannel] = (
        app_container.facilitators.otp_delivery_facilitator().available_channels()
    )
    if channels:
        LOGGER.info(
            "Login codes can be sent by: %s",
            ", ".join(sorted(channel.value for channel in channels)),
        )
        return

    log_level: int = (
        logging.ERROR
        if settings.environment is DeploymentEnvironment.PRODUCTION
        else logging.WARNING
    )
    LOGGER.log(
        log_level,
        "No login code provider is configured, so nobody can sign in. Set "
        "TWILIO_* (SMS), TELEGRAM_GATEWAY_API_TOKEN, WHATSAPP_OTP_* or SMTP_* "
        '(see .env.example, "Login codes").',
    )


def seed_demo_data(app_container: AppContainer) -> None:
    """
    SEED_DEMO_DATA (development only): create the demo businesses unless they
    exist, before the worker starts. Nothing is sent to any provider.
    """

    if not app_container.config.app_settings().is_demo_data_seeding_enabled:
        return

    report: DemoDataSeedReport = (
        app_container.operators.demo.seed_demo_data_operator().operate(
            SeedDemoDataCommand()
        )
    )
    # Without PUBLIC_DEMO_BUSINESS_IDS the landing page chats with these.
    app_container.registries.public_demo_directory().adopt_seeded(
        [*report.created_business_ids, *report.kept_business_ids]
    )
    # A warning, like the development login codes, so that uvicorn's default
    # log shows how to sign in.
    LOGGER.warning(
        "Demo data: %d business(es) created, %d already there. Sign in as the "
        "demo owner from docs/LAUNCH.md; in development the login code is "
        "printed in this log.",
        len(report.created_business_ids),
        len(report.kept_business_ids),
    )


def configure_platform_bot(app_container: AppContainer) -> None:
    """Register the platform bot's webhook when the bot is configured."""

    settings: AppSettings = app_container.config.app_settings()
    if (
        settings.telegram_platform_bot_token is None
        or settings.encryption_key is None
        or settings.app_base_url is None
    ):
        return

    channel_operators = app_container.operators.channels
    try:
        profile: TelegramBotProfile = (
            channel_operators.configure_platform_bot_webhook_operator().operate(
                PlatformBotWebhookSetup()
            )
        )
    except ApplicationError as error:
        LOGGER.warning("Platform bot webhook was not registered: %s", error)
        return

    LOGGER.info("Platform bot webhook registered for @%s", profile.username)


def close_postgres_pool(app_container: AppContainer) -> None:
    connection_pool: PostgresConnectionPoolClient | None = (
        app_container.clients.postgres_pool()
    )
    if connection_pool is not None:
        connection_pool.close()
