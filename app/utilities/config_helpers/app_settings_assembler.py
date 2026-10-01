"""Assemble AppSettings from environment variables (the external boundary)."""

import os
from collections.abc import Callable, Mapping

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.constrained_integers import (
    AutotestTurnLimit,
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.constrained_integers import (
    RecordingRetentionDays,
)
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    PublicBaseUrl,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.messaging.constrained_integers import SmtpPort
from app.schemas.typings.messaging.constrained_strings import (
    EmailSenderAddress,
    SmsSenderId,
    SmtpHost,
    TwilioAccountSid,
    TwilioMessagingServiceSid,
)
from app.schemas.typings.messaging.strings import SmtpUsername
from app.schemas.typings.platform.booleans import IsLlmContentTraced
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.schemas.typings.platform.strings import (
    DatabaseUrl,
    LocalDirectoryPath,
    PlatformIdentifier,
    PlatformSecret,
)
from app.schemas.typings.users.booleans import IsOtpCodeLoggingEnabled
from app.schemas.typings.users.constrained_integers import (
    OtpAttemptCount,
    OtpLifetimeSeconds,
    SessionLifetimeSeconds,
)
from app.schemas.typings.users.constrained_strings import EmailAddress

# The concept's choice: OpenAI gpt-5-mini in a project with EU data residency.
DEFAULT_LLM_PROVIDER: str = LlmProvider.OPENAI
DEFAULT_MODEL_IDS: dict[str, str] = {
    LlmProvider.OPENAI: "gpt-5-mini",
    LlmProvider.ANTHROPIC: "claude-opus-5-5",
    LlmProvider.SCRIPTED: "scripted",
}
DEFAULT_OPENAI_BASE_URL: str = "https://eu.api.openai.com/v1"
# Langfuse Cloud EU region (the concept keeps data in the EU).
DEFAULT_LANGFUSE_HOST: str = "https://cloud.langfuse.com"
# Global ElevenLabs API; set https://api.eu.residency.elevenlabs.io to keep
# voice data in the EU (concept section 7).
DEFAULT_ELEVENLABS_API_BASE_URL: str = "https://api.elevenlabs.io"
# Comprehensively sanctioned jurisdictions for a US-person founder. Confirm the
# list with a lawyer before launch; override with RESTRICTED_COUNTRY_CODES
# (comma-separated, an empty value disables the restriction).
DEFAULT_RESTRICTED_COUNTRY_CODES: str = "CU,IR,KP,SY"
DEFAULT_DPA_DOCUMENT_VERSION: str = "2026-10-01"
# Call recordings kept on this server (development or a single server);
# recordings of ElevenLabs calls stay in ElevenLabs storage.
DEFAULT_RECORDINGS_DIRECTORY: str = "var/recordings"
# Approved translations of the WhatsApp login code template; the first one
# is used when the user's language has none.
DEFAULT_WHATSAPP_OTP_TEMPLATE_LANGUAGES: str = "en"
DEFAULT_SMTP_PORTS: dict[SmtpSecurity, int] = {
    SmtpSecurity.STARTTLS: 587,
    SmtpSecurity.SSL: 465,
    SmtpSecurity.NONE: 25,
}
TWILIO_VARIABLES: tuple[str, ...] = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "TWILIO_MESSAGING_SERVICE_SID",
)
WHATSAPP_OTP_VARIABLES: tuple[str, ...] = (
    "WHATSAPP_OTP_PHONE_NUMBER_ID",
    "WHATSAPP_OTP_TEMPLATE",
    "WHATSAPP_OTP_ACCESS_TOKEN",
)
SMTP_VARIABLES: tuple[str, ...] = (
    "SMTP_HOST",
    "SMTP_FROM",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
)
TRUE_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES: frozenset[str] = frozenset({"0", "false", "no", "off"})


def get_app_settings() -> AppSettings:
    """Assemble validated settings from the process environment."""

    return assemble_app_settings(os.environ)


def assemble_app_settings(environment_variables: Mapping[str, str]) -> AppSettings:
    """Assemble validated settings from an explicit variable mapping."""

    environment = DeploymentEnvironment(
        read_text(environment_variables, "APP_ENV", DeploymentEnvironment.DEVELOPMENT)
    )
    is_development: bool = environment is not DeploymentEnvironment.PRODUCTION
    llm_provider = LlmProvider(
        read_text(environment_variables, "LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
    )
    default_model_id: str = DEFAULT_MODEL_IDS[llm_provider]

    def secret(variable_name: str) -> PlatformSecret | None:
        return optional_text(environment_variables, variable_name, PlatformSecret)

    def identifier(variable_name: str) -> PlatformIdentifier | None:
        return optional_text(environment_variables, variable_name, PlatformIdentifier)

    is_otp_code_logging_enabled: bool = read_boolean(
        environment_variables, "OTP_LOG_CODES", is_development
    )
    if is_otp_code_logging_enabled and not is_development:
        raise ValidationFailedError(
            "OTP_LOG_CODES cannot be enabled in production: login codes would be "
            "written to the log. Configure a login code provider instead."
        )

    check_login_code_providers(environment_variables)
    smtp_security = SmtpSecurity(
        read_text(environment_variables, "SMTP_SECURITY", SmtpSecurity.STARTTLS)
    )

    return AppSettings(
        environment=environment,
        app_base_url=optional_text(
            environment_variables,
            "APP_BASE_URL",
            PublicBaseUrl,
        ),
        database_url=optional_text(environment_variables, "DATABASE_URL", DatabaseUrl),
        encryption_key=secret("ENCRYPTION_KEY"),
        llm_provider=llm_provider,
        llm_model_id=LlmModelId(
            read_text(environment_variables, "LLM_MODEL_ID", default_model_id)
        ),
        llm_judge_model_id=LlmModelId(
            read_text(environment_variables, "LLM_JUDGE_MODEL_ID", default_model_id)
        ),
        llm_chat_effort=LlmEffort(
            read_text(environment_variables, "LLM_CHAT_EFFORT", LlmEffort.LOW)
        ),
        llm_judge_effort=LlmEffort(
            read_text(environment_variables, "LLM_JUDGE_EFFORT", LlmEffort.MEDIUM)
        ),
        llm_max_output_tokens=LlmMaxOutputTokens(
            read_integer(environment_variables, "LLM_MAX_OUTPUT_TOKENS", 16000)
        ),
        llm_tool_round_limit=LlmToolRoundLimit(
            read_integer(environment_variables, "LLM_TOOL_ROUND_LIMIT", 8)
        ),
        openai_base_url=PublicBaseUrl(
            read_text(environment_variables, "OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        ),
        openai_project_id=identifier("OPENAI_PROJECT_ID"),
        autotest_turn_limit=AutotestTurnLimit(
            read_integer(environment_variables, "AUTOTEST_TURN_LIMIT", 4)
        ),
        otp_lifetime_seconds=OtpLifetimeSeconds(
            read_integer(environment_variables, "OTP_LIFETIME_SECONDS", 600)
        ),
        otp_max_failed_attempts=OtpAttemptCount(
            read_integer(environment_variables, "OTP_MAX_FAILED_ATTEMPTS", 5)
        ),
        is_otp_code_logging_enabled=IsOtpCodeLoggingEnabled(
            is_otp_code_logging_enabled
        ),
        session_lifetime_seconds=SessionLifetimeSeconds(
            read_integer(
                environment_variables,
                "SESSION_LIFETIME_SECONDS",
                30 * 24 * 60 * 60,
            )
        ),
        restricted_country_codes=[
            CountryCode(country_code)
            for country_code in read_list(
                environment_variables,
                "RESTRICTED_COUNTRY_CODES",
                DEFAULT_RESTRICTED_COUNTRY_CODES,
            )
        ],
        default_data_region=DataRegion(
            read_text(environment_variables, "DEFAULT_DATA_REGION", DataRegion.EU)
        ),
        default_recording_retention_days=RecordingRetentionDays(
            read_integer(environment_variables, "RECORDING_RETENTION_DAYS", 90)
        ),
        contact_message_limit_per_hour=ContactMessageLimit(
            read_integer(environment_variables, "CONTACT_MESSAGE_LIMIT_PER_HOUR", 60)
        ),
        dpa_document_version=DpaDocumentVersion(
            read_text(
                environment_variables,
                "DPA_DOCUMENT_VERSION",
                DEFAULT_DPA_DOCUMENT_VERSION,
            )
        ),
        platform_admin_emails=[
            EmailAddress(email.lower())
            for email in read_raw_list(environment_variables, "PLATFORM_ADMIN_EMAILS")
        ],
        platform_admin_phone_numbers=[
            E164PhoneNumber(phone_number)
            for phone_number in read_raw_list(
                environment_variables,
                "PLATFORM_ADMIN_PHONE_NUMBERS",
            )
        ],
        twilio_account_sid=optional_setting(
            environment_variables, "TWILIO_ACCOUNT_SID", TwilioAccountSid
        ),
        twilio_auth_token=secret("TWILIO_AUTH_TOKEN"),
        twilio_sender=optional_setting(
            environment_variables, "TWILIO_FROM_NUMBER", SmsSenderId
        ),
        twilio_messaging_service_sid=optional_setting(
            environment_variables,
            "TWILIO_MESSAGING_SERVICE_SID",
            TwilioMessagingServiceSid,
        ),
        telegram_gateway_api_token=secret("TELEGRAM_GATEWAY_API_TOKEN"),
        whatsapp_otp_phone_number_id=optional_setting(
            environment_variables, "WHATSAPP_OTP_PHONE_NUMBER_ID", MetaObjectId
        ),
        # The platform's system user token usually serves both purposes.
        whatsapp_otp_access_token=(
            secret("WHATSAPP_OTP_ACCESS_TOKEN") or secret("WHATSAPP_SYSTEM_USER_TOKEN")
        ),
        whatsapp_otp_template_name=optional_setting(
            environment_variables, "WHATSAPP_OTP_TEMPLATE", WhatsAppTemplateName
        ),
        whatsapp_otp_template_languages=[
            parse_setting(
                "WHATSAPP_OTP_TEMPLATE_LANGUAGES",
                raw_language,
                WhatsAppTemplateLanguageCode,
            )
            for raw_language in (
                read_raw_list(environment_variables, "WHATSAPP_OTP_TEMPLATE_LANGUAGES")
                or [DEFAULT_WHATSAPP_OTP_TEMPLATE_LANGUAGES]
            )
        ],
        smtp_host=optional_setting(environment_variables, "SMTP_HOST", SmtpHost),
        smtp_port=parse_setting(
            "SMTP_PORT",
            read_integer(
                environment_variables,
                "SMTP_PORT",
                DEFAULT_SMTP_PORTS[smtp_security],
            ),
            SmtpPort,
        ),
        smtp_security=smtp_security,
        smtp_username=optional_setting(
            environment_variables, "SMTP_USERNAME", SmtpUsername
        ),
        smtp_password=secret("SMTP_PASSWORD"),
        smtp_sender=optional_setting(
            environment_variables, "SMTP_FROM", EmailSenderAddress
        ),
        elevenlabs_api_key=secret("ELEVENLABS_API_KEY"),
        elevenlabs_webhook_secret=secret("ELEVENLABS_WEBHOOK_SECRET"),
        elevenlabs_api_base_url=PublicBaseUrl(
            read_text(
                environment_variables,
                "ELEVENLABS_API_BASE_URL",
                DEFAULT_ELEVENLABS_API_BASE_URL,
            )
        ),
        zadarma_api_key=secret("ZADARMA_API_KEY"),
        zadarma_api_secret=secret("ZADARMA_API_SECRET"),
        meta_app_id=identifier("META_APP_ID"),
        meta_app_secret=secret("META_APP_SECRET"),
        meta_verify_token=secret("META_VERIFY_TOKEN"),
        whatsapp_system_user_token=secret("WHATSAPP_SYSTEM_USER_TOKEN"),
        whatsapp_notification_phone_number_id=optional_text(
            environment_variables,
            "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID",
            MetaObjectId,
        ),
        whatsapp_notification_template_name=optional_text(
            environment_variables,
            "WHATSAPP_NOTIFICATION_TEMPLATE",
            WhatsAppTemplateName,
        ),
        telegram_platform_bot_token=secret("TELEGRAM_PLATFORM_BOT_TOKEN"),
        google_oauth_client_id=identifier("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=secret("GOOGLE_OAUTH_CLIENT_SECRET"),
        flitt_merchant_id=identifier("FLITT_MERCHANT_ID"),
        flitt_secret_key=secret("FLITT_SECRET_KEY"),
        langfuse_public_key=identifier("LANGFUSE_PUBLIC_KEY"),
        langfuse_secret_key=secret("LANGFUSE_SECRET_KEY"),
        sentry_dsn=secret("SENTRY_DSN"),
        langfuse_host=PublicBaseUrl(
            read_text(environment_variables, "LANGFUSE_HOST", DEFAULT_LANGFUSE_HOST)
        ),
        is_llm_content_traced=IsLlmContentTraced(
            read_boolean(environment_variables, "LANGFUSE_CAPTURE_CONTENT", False)
        ),
        cors_allowed_origins=[
            PublicBaseUrl(origin)
            for origin in read_raw_list(environment_variables, "CORS_ALLOWED_ORIGINS")
        ],
        worker_poll_seconds=WorkerPollSeconds(
            read_integer(environment_variables, "WORKER_POLL_SECONDS", 15)
        ),
        recordings_directory=LocalDirectoryPath(
            read_text(
                environment_variables,
                "RECORDINGS_DIRECTORY",
                DEFAULT_RECORDINGS_DIRECTORY,
            )
        ),
    )


def check_login_code_providers(environment_variables: Mapping[str, str]) -> None:
    """
    A login code provider is configured completely or not at all, so a typo
    stops the start instead of silently hiding a sign-in channel.
    """

    present: set[str] = {
        variable_name
        for variable_name in (
            *TWILIO_VARIABLES,
            *WHATSAPP_OTP_VARIABLES,
            *SMTP_VARIABLES,
        )
        if environment_variables.get(variable_name, "").strip() != ""
    }
    has_twilio_sender: bool = bool(
        present & {"TWILIO_FROM_NUMBER", "TWILIO_MESSAGING_SERVICE_SID"}
    )
    if present & set(TWILIO_VARIABLES) and not (
        {"TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"} <= present and has_twilio_sender
    ):
        raise ValidationFailedError(
            "Login codes by SMS need TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and "
            "TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID."
        )

    has_whatsapp_token: bool = (
        "WHATSAPP_OTP_ACCESS_TOKEN" in present
        or environment_variables.get("WHATSAPP_SYSTEM_USER_TOKEN", "").strip() != ""
    )
    if present & set(WHATSAPP_OTP_VARIABLES) and not (
        {"WHATSAPP_OTP_PHONE_NUMBER_ID", "WHATSAPP_OTP_TEMPLATE"} <= present
        and has_whatsapp_token
    ):
        raise ValidationFailedError(
            "Login codes by WhatsApp need WHATSAPP_OTP_PHONE_NUMBER_ID, "
            "WHATSAPP_OTP_TEMPLATE and WHATSAPP_OTP_ACCESS_TOKEN (or "
            "WHATSAPP_SYSTEM_USER_TOKEN)."
        )

    has_smtp_login: bool = "SMTP_USERNAME" in present
    if present & set(SMTP_VARIABLES) and not (
        {"SMTP_HOST", "SMTP_FROM"} <= present
        and has_smtp_login == ("SMTP_PASSWORD" in present)
    ):
        raise ValidationFailedError(
            "Login codes by e-mail need SMTP_HOST and SMTP_FROM, and "
            "SMTP_USERNAME together with SMTP_PASSWORD when the server needs a "
            "login."
        )


def read_text(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: str,
) -> str:
    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return default_value

    return raw_value


def read_integer(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: int,
) -> int:
    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return default_value

    try:
        return int(raw_value)
    except ValueError as error:
        raise ValidationFailedError(
            f"{variable_name} must be an integer, got {raw_value!r}."
        ) from error


def read_boolean(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: bool,
) -> bool:
    raw_value: str = environment_variables.get(variable_name, "").strip().lower()
    if raw_value == "":
        return default_value

    if raw_value in TRUE_VALUES:
        return True

    if raw_value in FALSE_VALUES:
        return False

    raise ValidationFailedError(
        f"{variable_name} must be a boolean (true/false), got {raw_value!r}."
    )


def read_list(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: str,
) -> list[str]:
    raw_value: str = environment_variables.get(variable_name, default_value)
    items: list[str] = []
    for raw_item in raw_value.split(","):
        item: str = raw_item.strip().upper()
        if item != "":
            items.append(item)

    return items


def read_raw_list(
    environment_variables: Mapping[str, str],
    variable_name: str,
) -> list[str]:
    raw_value: str = environment_variables.get(variable_name, "")
    items: list[str] = []
    for raw_item in raw_value.split(","):
        item: str = raw_item.strip()
        if item != "":
            items.append(item)

    return items


def optional_setting[TypedValue](
    environment_variables: Mapping[str, str],
    variable_name: str,
    typed_value_type: Callable[[str], TypedValue],
) -> TypedValue | None:
    """A typed optional value; an invalid one names its variable."""

    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return None

    return parse_setting(variable_name, raw_value, typed_value_type)


def parse_setting[RawValue, TypedValue](
    variable_name: str,
    raw_value: RawValue,
    typed_value_type: Callable[[RawValue], TypedValue],
) -> TypedValue:
    try:
        return typed_value_type(raw_value)
    except ValueError as error:
        raise ValidationFailedError(f"{variable_name} has an invalid value.") from error


def optional_text[TypedText: str](
    environment_variables: Mapping[str, str],
    variable_name: str,
    typed_text_type: Callable[[str], TypedText],
) -> TypedText | None:
    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return None

    return typed_text_type(raw_value)
