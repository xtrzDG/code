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
from app.gateways.http.application import build_http_application
from app.gateways.http.router_assembly import build_application_routers
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.dto.channels import PlatformBotWebhookSetup, TelegramBotProfile
from app.schemas.exceptions.base_exception import ApplicationError

LOGGER: logging.Logger = logging.getLogger(__name__)
# Buffered model-call traces of the API process go to Langfuse this often
# (the worker flushes its own buffer as a periodic job).
TRACE_FLUSH_INTERVAL_SECONDS: float = 60.0


def create_application() -> FastAPI:
    """The API with settings from the environment (uvicorn factory)."""

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
    once), report the login code channels, point the platform Telegram bot
    at this API when it is configured, and start flushing model-call
    traces. Shutdown: flush the remaining traces and close the Postgres pool.
    """

    @asynccontextmanager
    async def lifespan(http_application: FastAPI) -> AsyncGenerator[None]:
        del http_application
        app_container.registries.country_registry().list_all()
        report_login_code_channels(app_container)
        configure_platform_bot(app_container)
        trace_facilitator: LlmTraceFacilitatorContract = (
            app_container.adapters.llm_trace_facilitator()
        )
        stop_event = threading.Event()
        flush_thread = start_trace_flushing(trace_facilitator, stop_event)
        try:
            yield
        finally:
            stop_event.set()
            flush_thread.join(timeout=TRACE_FLUSH_INTERVAL_SECONDS)
            trace_facilitator.flush()
            close_postgres_pool(app_container)

    return lifespan


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


def close_postgres_pool(app_container: AppContainer) -> None:
    connection_pool: PostgresConnectionPoolClient | None = (
        app_container.clients.postgres_pool()
    )
    if connection_pool is not None:
        connection_pool.close()
