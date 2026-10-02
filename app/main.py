"""
HTTP entry point (uvicorn factory):

    uv run uvicorn app.main:create_application --factory
"""

import logging
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.types import Lifespan

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.containers.app import AppContainer
from app.contracts.observability import LlmTraceFacilitatorContract
from app.gateways.http.access_log_redaction import install_access_log_redaction
from app.gateways.http.application import build_http_application
from app.gateways.http.router_assembly import build_application_routers
from app.gateways.worker.background_worker import BackgroundWorker
from app.registries.demo.demo_dataset_registry import (
    DEMO_OWNER_EMAIL,
    DEMO_OWNER_PHONE_NUMBER,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.dto.channels import PlatformBotWebhookSetup, TelegramBotProfile
from app.schemas.dto.demo_data import DemoDataSeedReport, SeedDemoDataCommand
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import ENGLISH_LOCALE_IDENTIFIER

LOGGER: logging.Logger = logging.getLogger(__name__)
# Buffered model-call traces of the API process go to Langfuse this often
# (the worker flushes its own buffer as a periodic job).
TRACE_FLUSH_INTERVAL_SECONDS: float = 60.0
# On shutdown the embedded worker finishes its current tick; a tick still
# running after this long (a long autotest run) is abandoned with a warning.
EMBEDDED_WORKER_STOP_SECONDS: float = 30.0
EMBEDDED_WORKER_THREAD_NAME: str = "embedded-background-worker"


def create_application() -> FastAPI:
    """The API with settings from the environment (uvicorn factory)."""

    install_access_log_redaction()
    return build_application(AppContainer())


def build_application(app_container: AppContainer) -> FastAPI:
    """The API over a ready container (tests pass one with overrides)."""

    settings: AppSettings = app_container.config.app_settings()
    return build_http_application(
        routers=build_application_routers(app_container),
        error_reporter=app_container.facilitators.error_reporter(),
        cors_allowed_origins=settings.cors_allowed_origins,
        lifespan=build_lifespan(app_container),
    )


def build_lifespan(app_container: AppContainer) -> Lifespan[FastAPI]:
    """
    Startup: warm the country catalog (every country's profile is built
    once), check that the configured DPA has its text in this build, report
    the login code channels, with SEED_DEMO_DATA fill the instance with the
    demo businesses (once), point the platform Telegram bot
    at this API when it is configured, start flushing model-call traces and,
    with EMBEDDED_WORKER, start the background worker in a thread. Shutdown:
    stop the worker after its current tick, flush the remaining traces and
    close the Postgres pool.
    """

    @asynccontextmanager
    async def lifespan(http_application: FastAPI) -> AsyncGenerator[None]:
        del http_application
        app_container.registries.country_registry().list_all()
        check_dpa_document(app_container)
        report_login_code_channels(app_container)
        seed_demo_data(app_container)
        configure_platform_bot(app_container)
        trace_facilitator: LlmTraceFacilitatorContract = (
            app_container.adapters.llm_trace_facilitator()
        )
        stop_event = threading.Event()
        flush_thread = start_trace_flushing(trace_facilitator, stop_event)
        worker_thread: threading.Thread | None = None
        try:
            worker_thread = start_embedded_worker(app_container, stop_event)
            yield
        finally:
            stop_event.set()
            if worker_thread is not None:
                stop_embedded_worker(worker_thread)
            flush_thread.join(timeout=TRACE_FLUSH_INTERVAL_SECONDS)
            trace_facilitator.flush()
            close_postgres_pool(app_container)

    return lifespan


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
        app_container.operators.seed_demo_data_operator().operate(SeedDemoDataCommand())
    )
    # A warning, like the development login codes, so that uvicorn's default
    # log shows how to sign in.
    LOGGER.warning(
        "Demo data: %d business(es) created, %d already there. Sign in with "
        "%s or %s; in development the login code is printed in this log.",
        len(report.created_business_ids),
        len(report.kept_business_ids),
        DEMO_OWNER_PHONE_NUMBER,
        DEMO_OWNER_EMAIL,
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

    try:
        profile: TelegramBotProfile = (
            app_container.operators.configure_platform_bot_webhook_operator().operate(
                PlatformBotWebhookSetup()
            )
        )
    except ApplicationError as error:
        LOGGER.warning("Platform bot webhook was not registered: %s", error)
        return

    LOGGER.info("Platform bot webhook registered for @%s", profile.username)


def start_trace_flushing(
    trace_facilitator: LlmTraceFacilitatorContract,
    stop_event: threading.Event,
) -> threading.Thread:
    """Daemon thread that flushes buffered traces until `stop_event` is set."""

    def flush_periodically() -> None:
        while not stop_event.wait(timeout=TRACE_FLUSH_INTERVAL_SECONDS):
            trace_facilitator.flush()

    flush_thread = threading.Thread(
        target=flush_periodically,
        name="llm-trace-flush",
        daemon=True,
    )
    flush_thread.start()
    return flush_thread


def start_embedded_worker(
    app_container: AppContainer,
    stop_event: threading.Event,
) -> threading.Thread | None:
    """
    With EMBEDDED_WORKER, run the background worker (the same periodic jobs
    and job queue as `app.worker_main`) in a daemon thread until
    `stop_event` is set; otherwise nothing is started.
    """

    settings: AppSettings = app_container.config.app_settings()
    if not settings.is_embedded_worker_enabled:
        return None

    worker: BackgroundWorker = app_container.gateways.background_worker()
    worker_thread = threading.Thread(
        target=worker.run_forever,
        args=(stop_event,),
        name=EMBEDDED_WORKER_THREAD_NAME,
        daemon=True,
    )
    worker_thread.start()
    LOGGER.info(
        "Background worker runs inside the API (EMBEDDED_WORKER); do not start "
        "app.worker_main next to it"
    )
    return worker_thread


def stop_embedded_worker(worker_thread: threading.Thread) -> None:
    """Wait for the worker's current tick (its stop event is already set)."""

    worker_thread.join(timeout=EMBEDDED_WORKER_STOP_SECONDS)
    if worker_thread.is_alive():
        LOGGER.warning(
            "Embedded background worker did not finish its tick within %.0f s; "
            "abandoning it",
            EMBEDDED_WORKER_STOP_SECONDS,
        )
        return

    LOGGER.info("Embedded background worker stopped")


def close_postgres_pool(app_container: AppContainer) -> None:
    connection_pool: PostgresConnectionPoolClient | None = (
        app_container.clients.postgres_pool()
    )
    if connection_pool is not None:
        connection_pool.close()
