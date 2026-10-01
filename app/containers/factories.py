"""
Small builders the containers use where a provider depends on optional
settings (a missing key switches to a stand-in instead of failing startup).
"""

from pathlib import Path

from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.elevenlabs.unconfigured_elevenlabs_client import (
    UnconfiguredElevenLabsClient,
)
from app.clients.email.smtp_email_client import SmtpEmailClient
from app.clients.flitt.flitt_client import FlittClient
from app.clients.google.google_calendar_client import (
    GoogleCalendarClient,
    build_google_calendar_redirect_url,
)
from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.clients.meta.whatsapp_authentication_client import (
    WhatsAppAuthenticationClient,
)
from app.clients.telegram.telegram_gateway_client import TelegramGatewayClient
from app.clients.twilio.twilio_messaging_client import TwilioMessagingClient
from app.contracts.channel_clients import ElevenLabsApiClientContract
from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.messaging_clients import (
    EmailSenderClientContract,
    SmsMessagingClientContract,
    TelegramGatewayClientContract,
    WhatsAppAuthenticationClientContract,
)
from app.contracts.observability import LlmTraceFacilitatorContract
from app.facilitators.observability.langfuse_trace_facilitator import (
    LangfuseTraceFacilitator,
)
from app.facilitators.observability.null_trace_facilitator import (
    NullTraceFacilitator,
)
from app.facilitators.users.email_otp_delivery_facilitator import (
    EmailOtpDeliveryFacilitator,
)
from app.facilitators.users.logging_otp_delivery_facilitator import (
    LoggingOtpDeliveryFacilitator,
)
from app.facilitators.users.routing_otp_delivery_facilitator import (
    RoutingOtpDeliveryFacilitator,
)
from app.facilitators.users.sms_otp_delivery_facilitator import (
    SmsOtpDeliveryFacilitator,
)
from app.facilitators.users.telegram_gateway_otp_delivery_facilitator import (
    TelegramGatewayOtpDeliveryFacilitator,
)
from app.facilitators.users.whatsapp_otp_delivery_facilitator import (
    WhatsAppOtpDeliveryFacilitator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmProvider
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.utilities.conversations.llm_models import resolve_llm_provider

# Menu import reads photos and PDFs with an OpenAI vision model (brain slice);
# used when the chat model itself is not an OpenAI model.
DEFAULT_MENU_EXTRACTION_MODEL_ID: LlmModelId = LlmModelId("gpt-5-mini")


def build_elevenlabs_client(settings: AppSettings) -> ElevenLabsApiClientContract:
    """The ElevenLabs API client, or a stand-in that reports the missing key."""

    if settings.elevenlabs_api_key is None:
        return UnconfiguredElevenLabsClient()

    return ElevenLabsClient(
        api_key=settings.elevenlabs_api_key,
        base_url=settings.elevenlabs_api_base_url,
    )


def build_flitt_client(settings: AppSettings) -> FlittClient | None:
    """Flitt client when both merchant settings are present, else None."""

    if settings.flitt_merchant_id is None or settings.flitt_secret_key is None:
        return None

    return FlittClient(
        merchant_id=settings.flitt_merchant_id,
        secret_key=settings.flitt_secret_key,
    )


def build_google_calendar_client(settings: AppSettings) -> GoogleCalendarClient:
    """Google Calendar client; missing settings make its calls fail with 502."""

    return GoogleCalendarClient(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        redirect_url=build_google_calendar_redirect_url(settings.app_base_url),
    )


def build_langfuse_ingestion_client(
    settings: AppSettings,
) -> LangfuseIngestionClient | None:
    """Langfuse client when both keys are set, else None (no quality journal)."""

    if settings.langfuse_public_key is None or settings.langfuse_secret_key is None:
        return None

    return LangfuseIngestionClient(
        host=settings.langfuse_host,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
    )


def build_twilio_messaging_client(
    settings: AppSettings,
) -> TwilioMessagingClient | None:
    """Twilio SMS client when the account and a sender are set, else None."""

    if (
        settings.twilio_account_sid is None
        or settings.twilio_auth_token is None
        or (
            settings.twilio_sender is None
            and settings.twilio_messaging_service_sid is None
        )
    ):
        return None

    return TwilioMessagingClient(
        account_sid=settings.twilio_account_sid,
        auth_token=settings.twilio_auth_token,
        sender=settings.twilio_sender,
        messaging_service_sid=settings.twilio_messaging_service_sid,
    )


def build_telegram_gateway_client(
    settings: AppSettings,
) -> TelegramGatewayClient | None:
    """Telegram Gateway client when its token is set, else None."""

    if settings.telegram_gateway_api_token is None:
        return None

    return TelegramGatewayClient(api_token=settings.telegram_gateway_api_token)


def build_whatsapp_authentication_client(
    settings: AppSettings,
) -> WhatsAppAuthenticationClient | None:
    """WhatsApp login code client when the number, template and token are set."""

    if (
        settings.whatsapp_otp_phone_number_id is None
        or settings.whatsapp_otp_template_name is None
        or settings.whatsapp_otp_access_token is None
    ):
        return None

    return WhatsAppAuthenticationClient(
        access_token=settings.whatsapp_otp_access_token,
        phone_number_id=settings.whatsapp_otp_phone_number_id,
        template_name=settings.whatsapp_otp_template_name,
    )


def build_smtp_email_client(settings: AppSettings) -> SmtpEmailClient | None:
    """SMTP client when the server and the sender are set, else None."""

    if settings.smtp_host is None or settings.smtp_sender is None:
        return None

    return SmtpEmailClient(
        host=settings.smtp_host,
        port=settings.smtp_port,
        security=settings.smtp_security,
        sender=settings.smtp_sender,
        username=settings.smtp_username,
        password=settings.smtp_password,
    )


def build_otp_delivery_facilitator(
    settings: AppSettings,
    sms_client: SmsMessagingClientContract | None,
    telegram_gateway_client: TelegramGatewayClientContract | None,
    whatsapp_client: WhatsAppAuthenticationClientContract | None,
    email_client: EmailSenderClientContract | None,
    localized_text_resolver: LocalizedTextResolverContract,
) -> OtpDeliveryFacilitatorContract:
    """
    Login code delivery: each channel goes through its configured provider.
    In development and test (OTP_LOG_CODES) the remaining channels write
    the code to the log; in production a channel without a provider is not
    offered, and with no provider at all every sign-in fails with a clear
    error (also logged at startup by `app.main`).
    """

    providers: dict[OtpDeliveryChannel, OtpDeliveryFacilitatorContract] = {}
    if sms_client is not None:
        providers[OtpDeliveryChannel.SMS] = SmsOtpDeliveryFacilitator(
            sms_client=sms_client,
            localized_text_resolver=localized_text_resolver,
            app_settings=settings,
        )

    if telegram_gateway_client is not None:
        providers[OtpDeliveryChannel.TELEGRAM] = TelegramGatewayOtpDeliveryFacilitator(
            gateway_client=telegram_gateway_client,
            app_settings=settings,
        )

    if whatsapp_client is not None:
        providers[OtpDeliveryChannel.WHATSAPP] = WhatsAppOtpDeliveryFacilitator(
            whatsapp_client=whatsapp_client,
            template_languages=settings.whatsapp_otp_template_languages,
        )

    if email_client is not None:
        providers[OtpDeliveryChannel.EMAIL] = EmailOtpDeliveryFacilitator(
            email_client=email_client,
            localized_text_resolver=localized_text_resolver,
            app_settings=settings,
        )

    logging_facilitator = LoggingOtpDeliveryFacilitator(settings)
    for channel in logging_facilitator.available_channels():
        providers.setdefault(channel, logging_facilitator)

    return RoutingOtpDeliveryFacilitator(providers)


def build_llm_trace_facilitator(
    langfuse_client: LangfuseIngestionClient | None,
) -> LlmTraceFacilitatorContract:
    """Langfuse journal when configured, otherwise traces are discarded."""

    if langfuse_client is None:
        return NullTraceFacilitator()

    return LangfuseTraceFacilitator(client=langfuse_client)


def select_menu_extraction_model_id(settings: AppSettings) -> LlmModelId:
    """The chat model when it is an OpenAI model, else the default vision model."""

    if resolve_llm_provider(settings.llm_model_id) is LlmProvider.OPENAI:
        return settings.llm_model_id

    return DEFAULT_MENU_EXTRACTION_MODEL_ID


def resolve_recordings_directory(settings: AppSettings) -> Path:
    """Directory of call recordings kept on this server."""

    return Path(str(settings.recordings_directory))
