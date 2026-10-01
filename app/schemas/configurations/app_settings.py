from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import DataRegion
from app.schemas.typings.assistants.constrained_integers import (
    AutotestTurnLimit,
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.constrained_integers import (
    RecordingRetentionDays,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.platform.booleans import IsLlmContentTraced
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.schemas.typings.platform.strings import (
    DatabaseUrl,
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


class AppSettings(ImmutableDTO):
    """
    Validated runtime settings assembled from environment variables.

    Variable names follow the concept (section 14) where it names them; see
    `.env.example`.
    """

    environment: DeploymentEnvironment
    app_base_url: PublicBaseUrl | None = None
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
    is_otp_code_logging_enabled: IsOtpCodeLoggingEnabled
    session_lifetime_seconds: SessionLifetimeSeconds
    restricted_country_codes: list[CountryCode]
    default_data_region: DataRegion
    default_recording_retention_days: RecordingRetentionDays
    contact_message_limit_per_hour: ContactMessageLimit
    dpa_document_version: DpaDocumentVersion
    platform_admin_emails: list[EmailAddress]
    platform_admin_phone_numbers: list[E164PhoneNumber]
    elevenlabs_api_key: PlatformSecret | None = None
    elevenlabs_webhook_secret: PlatformSecret | None = None
    zadarma_api_key: PlatformSecret | None = None
    zadarma_api_secret: PlatformSecret | None = None
    meta_app_id: PlatformIdentifier | None = None
    meta_app_secret: PlatformSecret | None = None
    meta_verify_token: PlatformSecret | None = None
    whatsapp_system_user_token: PlatformSecret | None = None
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
    sentry_dsn: PlatformSecret | None = None
