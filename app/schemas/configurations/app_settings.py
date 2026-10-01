from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.messaging import SmtpSecurity
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
from app.schemas.typings.platform.booleans import (
    IsEmbeddedWorkerEnabled,
    IsLlmContentTraced,
)
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
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
    OtpSendLimit,
    SessionLifetimeSeconds,
)
from app.schemas.typings.users.constrained_strings import EmailAddress


class AppSettings(ImmutableDTO):
    """
    Validated runtime settings assembled from environment variables.

    Variable names follow the concept (section 14) where it names them; see
    `.env.example`.
    """

    environment: DeploymentEnvironment
    app_base_url: PublicBaseUrl | None = None
    # Public address of the owner cabinet; provider consent pages (Google
    # Calendar) send owners back there.
    cabinet_base_url: CabinetBaseUrl | None = None
    database_url: DatabaseUrl | None = None
    encryption_key: PlatformSecret | None = None
    llm_provider: LlmProvider
    llm_model_id: LlmModelId
    llm_judge_model_id: LlmModelId
    llm_chat_effort: LlmEffort
    llm_judge_effort: LlmEffort
    llm_max_output_tokens: LlmMaxOutputTokens
    llm_tool_round_limit: LlmToolRoundLimit
    openai_base_url: PublicBaseUrl
    openai_project_id: PlatformIdentifier | None = None
    autotest_turn_limit: AutotestTurnLimit
    otp_lifetime_seconds: OtpLifetimeSeconds
    otp_max_failed_attempts: OtpAttemptCount
    otp_sends_per_destination_per_hour: OtpSendLimit = OtpSendLimit(5)
    otp_sends_per_ip_per_hour: OtpSendLimit = OtpSendLimit(10)
    otp_sends_per_hour: OtpSendLimit = OtpSendLimit(300)
    is_otp_code_logging_enabled: IsOtpCodeLoggingEnabled
    session_lifetime_seconds: SessionLifetimeSeconds
    restricted_country_codes: list[CountryCode]
    default_data_region: DataRegion
    default_recording_retention_days: RecordingRetentionDays
    contact_message_limit_per_hour: ContactMessageLimit
    dpa_document_version: DpaDocumentVersion
    platform_admin_emails: list[EmailAddress]
    platform_admin_phone_numbers: list[E164PhoneNumber]
    # Login codes: one provider per delivery channel; a channel without a
    # provider is not offered (see `.env.example`, "Login codes").
    twilio_account_sid: TwilioAccountSid | None = None
    twilio_auth_token: PlatformSecret | None = None
    twilio_sender: SmsSenderId | None = None
    twilio_messaging_service_sid: TwilioMessagingServiceSid | None = None
    telegram_gateway_api_token: PlatformSecret | None = None
    whatsapp_otp_phone_number_id: MetaObjectId | None = None
    whatsapp_otp_access_token: PlatformSecret | None = None
    whatsapp_otp_template_name: WhatsAppTemplateName | None = None
    whatsapp_otp_template_languages: list[WhatsAppTemplateLanguageCode]
    smtp_host: SmtpHost | None = None
    smtp_port: SmtpPort = SmtpPort(587)
    smtp_security: SmtpSecurity = SmtpSecurity.STARTTLS
    smtp_username: SmtpUsername | None = None
    smtp_password: PlatformSecret | None = None
    smtp_sender: EmailSenderAddress | None = None
    elevenlabs_api_key: PlatformSecret | None = None
    elevenlabs_webhook_secret: PlatformSecret | None = None
    elevenlabs_api_base_url: PublicBaseUrl = PublicBaseUrl(
        "https://api.eu.residency.elevenlabs.io"
    )
    zadarma_api_key: PlatformSecret | None = None
    zadarma_api_secret: PlatformSecret | None = None
    meta_app_id: PlatformIdentifier | None = None
    meta_app_secret: PlatformSecret | None = None
    meta_verify_token: PlatformSecret | None = None
    whatsapp_system_user_token: PlatformSecret | None = None
    whatsapp_notification_phone_number_id: MetaObjectId | None = None
    whatsapp_notification_template_name: WhatsAppTemplateName | None = None
    whatsapp_reminder_template_name: WhatsAppTemplateName | None = None
    telegram_platform_bot_token: PlatformSecret | None = None
    google_oauth_client_id: PlatformIdentifier | None = None
    google_oauth_client_secret: PlatformSecret | None = None
    flitt_merchant_id: PlatformIdentifier | None = None
    flitt_secret_key: PlatformSecret | None = None
    langfuse_public_key: PlatformIdentifier | None = None
    langfuse_secret_key: PlatformSecret | None = None
    langfuse_host: PublicBaseUrl
    is_llm_content_traced: IsLlmContentTraced
    cors_allowed_origins: list[PublicBaseUrl]
    worker_poll_seconds: WorkerPollSeconds
    # The API runs the background worker in a thread of its own process
    # (EMBEDDED_WORKER; see `read_embedded_worker`).
    is_embedded_worker_enabled: IsEmbeddedWorkerEnabled = IsEmbeddedWorkerEnabled(False)
    sentry_dsn: PlatformSecret | None = None
    recordings_directory: LocalDirectoryPath = LocalDirectoryPath("var/recordings")
