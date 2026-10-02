from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.constants.observability import LogFormat
from app.schemas.typings.assistants.constrained_integers import (
    AutotestTurnLimit,
    LlmCallTimeoutSeconds,
    LlmConcurrencyLimit,
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
    PhoneNumberPrefix,
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
    IsDemoDataSeedingEnabled,
    IsEmbeddedWorkerEnabled,
    IsLlmContentTraced,
)
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from app.schemas.typings.platform.constrained_integers import (
    DatabasePoolSize,
    ThreadPoolSize,
    WorkerLaneConcurrency,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import (
    CabinetBaseUrl,
    ReleaseVersion,
)
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
    OtpVerifyLimit,
    SessionLifetimeSeconds,
)
from app.schemas.typings.users.constrained_strings import (
    EmailAddress,
    TurnstileSiteKey,
)


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
    # One model call of a customer chat: its timeout (retried once).
    llm_call_timeout_seconds: LlmCallTimeoutSeconds = LlmCallTimeoutSeconds(25)
    # Model calls of one process at once (LLM_MAX_CONCURRENCY).
    llm_max_concurrency: LlmConcurrencyLimit = LlmConcurrencyLimit(32)
    openai_base_url: PublicBaseUrl
    openai_project_id: PlatformIdentifier | None = None
    autotest_turn_limit: AutotestTurnLimit
    otp_lifetime_seconds: OtpLifetimeSeconds
    otp_max_failed_attempts: OtpAttemptCount
    otp_sends_per_destination_per_hour: OtpSendLimit = OtpSendLimit(5)
    otp_sends_per_ip_per_hour: OtpSendLimit = OtpSendLimit(10)
    otp_sends_per_hour: OtpSendLimit = OtpSendLimit(300)
    # Login abuse limits (see `.env.example`, "Login abuse protection"):
    # codes to phones of one country, codes to the phones and e-mails of
    # verified users (their own budget), code checks per client address.
    otp_sends_per_country_per_hour: OtpSendLimit = OtpSendLimit(100)
    otp_sends_to_verified_users_per_hour: OtpSendLimit = OtpSendLimit(300)
    otp_verifies_per_ip_per_10_minutes: OtpVerifyLimit = OtpVerifyLimit(20)
    otp_high_risk_country_codes: list[CountryCode] = Field(
        default_factory=list[CountryCode]
    )
    otp_denied_phone_prefixes: list[PhoneNumberPrefix] = Field(
        default_factory=list[PhoneNumberPrefix]
    )
    # Cloudflare Turnstile bot check of risky code requests; off unless both
    # keys are set.
    turnstile_site_key: TurnstileSiteKey | None = None
    turnstile_secret_key: PlatformSecret | None = None
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
    # Request handlers running at once in threads (THREADPOOL_SIZE) and the
    # Postgres connections of one process (DB_POOL_SIZE, as many by default).
    threadpool_size: ThreadPoolSize = ThreadPoolSize(64)
    db_pool_size: DatabasePoolSize = DatabasePoolSize(64)
    worker_poll_seconds: WorkerPollSeconds
    # Threads per lane of each worker process (WORKER_LANE_CONCURRENCY).
    worker_lane_concurrency: dict[JobLane, WorkerLaneConcurrency]
    # The API runs the background worker in a thread of its own process
    # (EMBEDDED_WORKER; see `read_embedded_worker`).
    is_embedded_worker_enabled: IsEmbeddedWorkerEnabled = IsEmbeddedWorkerEnabled(False)
    # Development only: the API fills an empty instance with demo businesses
    # at startup (SEED_DEMO_DATA; refused in production).
    is_demo_data_seeding_enabled: IsDemoDataSeedingEnabled = IsDemoDataSeedingEnabled(
        False
    )
    sentry_dsn: PlatformSecret | None = None
    sentry_traces_sample_rate: TraceSampleRate = TraceSampleRate(0.05)
    # The deployed build (APP_RELEASE, on Render RENDER_GIT_COMMIT): error
    # reports and worker heartbeats name it.
    release_version: ReleaseVersion | None = None
    log_format: LogFormat = LogFormat.TEXT
    recordings_directory: LocalDirectoryPath = LocalDirectoryPath("var/recordings")
