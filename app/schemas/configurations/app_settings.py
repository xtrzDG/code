from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.configurations.backup_settings import BackupSettings
from app.schemas.configurations.media_settings import MediaSettings
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.configurations.privacy_settings import PrivacySettings
from app.schemas.configurations.reply_safety_settings import ReplySafetySettings
from app.schemas.configurations.reply_speed_settings import ReplySpeedSettings
from app.schemas.configurations.session_settings import SessionSettings
from app.schemas.configurations.support_settings import SupportSettings
from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.constants.observability import LogFormat
from app.schemas.constants.storage import RecordingStorageKind
from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.typings.assistants.constrained_integers import (
    AutotestTurnLimit,
    LlmCallTimeoutSeconds,
    LlmConcurrencyLimit,
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
    ScriptedLlmLatencyMilliseconds,
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
from app.schemas.typings.mfa.constrained_integers import StepUpMaxAgeSeconds
from app.schemas.typings.mfa.strings import TotpIssuerName
from app.schemas.typings.notifications.constrained_strings import (
    VapidPublicKey,
    VapidSubject,
)
from app.schemas.typings.platform.booleans import (
    IsDemoDataSeedingEnabled,
    IsEmbeddedWorkerEnabled,
    IsLlmContentTraced,
)
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from app.schemas.typings.platform.constrained_integers import (
    DatabaseIdleSeconds,
    DatabasePoolMinSize,
    DatabasePoolSize,
    TestChatConcurrencyLimit,
    ThreadPoolSize,
    WorkerLaneConcurrency,
    WorkerLanePollSeconds,
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
    # The cabinet's live updates LISTEN on this direct (session) connection
    # when DATABASE_URL goes through a transaction pooler; DATABASE_URL
    # otherwise (LIVE_EVENTS_DATABASE_URL).
    live_events_database_url: DatabaseUrl | None = None
    # The key ring (ENCRYPTION_KEYS, newest first, then ENCRYPTION_KEY): the
    # current key encrypts and signs; the previous ones only decrypt and
    # verify what they sealed until `rotate_encrypted_secrets` moved it.
    encryption_key: PlatformSecret | None = Field(default=None, repr=False)
    previous_encryption_keys: list[PlatformSecret] = Field(
        default_factory=list[PlatformSecret], repr=False
    )
    llm_provider: LlmProvider
    llm_model_id: LlmModelId
    llm_judge_model_id: LlmModelId
    # Call summaries for staff (LLM_SUMMARY_MODEL_ID); None: the chat model.
    llm_summary_model_id: LlmModelId | None = None
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
    # The scripted model's wait before each answer (load tests).
    scripted_llm_latency_ms: ScriptedLlmLatencyMilliseconds = (
        ScriptedLlmLatencyMilliseconds(0)
    )
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
    # Two-factor sign-in: how long a sign-in or a confirmation covers
    # sensitive actions, and the name authenticator apps show.
    step_up_max_age_seconds: StepUpMaxAgeSeconds = StepUpMaxAgeSeconds(600)
    mfa_issuer_name: TotpIssuerName = TotpIssuerName("Assistant Workshop")
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
    # The owners' digests and monthly reports on WhatsApp (an approved
    # utility template with three body parameters; .env.example).
    whatsapp_owner_report_template_name: WhatsAppTemplateName | None = None
    telegram_platform_bot_token: PlatformSecret | None = None
    google_oauth_client_id: PlatformIdentifier | None = None
    google_oauth_client_secret: PlatformSecret | None = None
    flitt_merchant_id: PlatformIdentifier | None = None
    flitt_secret_key: PlatformSecret | None = None
    # Notifications on the devices of cabinet users (Web Push, VAPID); off
    # unless all three are set (see `.env.example`, "Staff notifications").
    web_push_vapid_public_key: VapidPublicKey | None = None
    web_push_vapid_private_key: PlatformSecret | None = None
    web_push_vapid_subject: VapidSubject | None = None
    langfuse_public_key: PlatformIdentifier | None = None
    langfuse_secret_key: PlatformSecret | None = None
    langfuse_host: PublicBaseUrl
    is_llm_content_traced: IsLlmContentTraced
    cors_allowed_origins: list[PublicBaseUrl]
    # Request handlers running at once in threads (THREADPOOL_SIZE) and the
    # Postgres connections of one process (DB_POOL_SIZE, half as many by
    # default: a thread waiting for the model holds no connection).
    threadpool_size: ThreadPoolSize = ThreadPoolSize(64)
    db_pool_size: DatabasePoolSize = DatabasePoolSize(32)
    # Idle connections close after DB_POOL_MAX_IDLE_SECONDS down to
    # DB_POOL_MIN_SIZE (docs/operations/capacity.md, the connection budget).
    db_pool_min_size: DatabasePoolMinSize = DatabasePoolMinSize(2)
    db_pool_max_idle_seconds: DatabaseIdleSeconds = DatabaseIdleSeconds(300)
    # Owner test-chat turns one API process answers at once.
    test_chat_max_concurrency: TestChatConcurrencyLimit = TestChatConcurrencyLimit(4)
    worker_poll_seconds: WorkerPollSeconds
    # The worker's safety-net poll of customer messages, which NOTIFY
    # normally hands over at once (WORKER_INBOUND_POLL_SECONDS).
    worker_inbound_poll_seconds: WorkerLanePollSeconds = WorkerLanePollSeconds(2)
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
    # Where recordings this platform keeps live (RECORDINGS_STORAGE): files
    # under RECORDINGS_DIRECTORY in development, EU object storage
    # (RECORDINGS_S3_*), encrypted per business, in production.
    recording_storage_kind: RecordingStorageKind = RecordingStorageKind.LOCAL
    recordings_object_storage: ObjectStorageConnection | None = None
    # Off-site backups and the restore drill (BACKUP_*; `workshop backup`,
    # `workshop restore-check`, docs/operations/backup-restore.md).
    backup: BackupSettings = Field(default_factory=BackupSettings)
    # Voice notes and photos of customers (LLM_TRANSCRIBE_MODEL, MEDIA_MAX_*).
    media: MediaSettings = Field(default_factory=MediaSettings)
    # Grouped bursts, the turn deadline and model failover
    # (MESSAGE_COALESCE_SECONDS, CHAT_TURN_DEADLINE_SECONDS, LLM_FALLBACK_MODEL_ID).
    reply_speed: ReplySpeedSettings = Field(default_factory=ReplySpeedSettings)
    # The claim check and the prompt-injection brake of the reply guard
    # (LLM_VERIFIER_MODEL_ID, INJECTION_FLAG_LIMIT).
    reply_safety: ReplySafetySettings = Field(default_factory=ReplySafetySettings)
    # Where the platform alerts go (PLATFORM_ALERT_*, docs/operations/slo.md).
    platform_alerts: PlatformAlertSettings = Field(
        default_factory=PlatformAlertSettings
    )
    # When unused and admin sessions end (SESSION_IDLE_TIMEOUT_SECONDS,
    # ADMIN_SESSION_IDLE_TIMEOUT_SECONDS, ADMIN_SESSION_LIFETIME_SECONDS).
    sessions: SessionSettings = Field(default_factory=SessionSettings)
    # The cabinet's "Help and support" contacts (SUPPORT_*).
    support: SupportSettings = Field(default_factory=SupportSettings)
    # The suppression list's key and the full exports' link (SUPPRESSION_LIST_KEY,
    # BUSINESS_EXPORT_LINK_HOURS).
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
