from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import DataRegion
from app.schemas.typings.accounts.booleans import IsOtpCodeLoggingEnabled
from app.schemas.typings.accounts.constrained_integers import (
    OtpAttemptCount,
    OtpLifetimeSeconds,
    SessionLifetimeSeconds,
)
from app.schemas.typings.assistants.constrained_integers import (
    AutotestTurnLimit,
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    WebhookVerificationToken,
)
from app.schemas.typings.localization.constrained_strings import CountryCode


class AppSettings(ImmutableDTO):
    """
    Validated runtime settings assembled from environment variables.

    See `.env.example` for the variable names and defaults.
    """

    environment: DeploymentEnvironment
    llm_model_id: LlmModelId
    llm_judge_model_id: LlmModelId
    llm_chat_effort: LlmEffort
    llm_judge_effort: LlmEffort
    llm_max_output_tokens: LlmMaxOutputTokens
    llm_tool_round_limit: LlmToolRoundLimit
    autotest_turn_limit: AutotestTurnLimit
    otp_lifetime_seconds: OtpLifetimeSeconds
    otp_max_failed_attempts: OtpAttemptCount
    is_otp_code_logging_enabled: IsOtpCodeLoggingEnabled
    session_lifetime_seconds: SessionLifetimeSeconds
    restricted_country_codes: list[CountryCode]
    default_data_region: DataRegion
    public_base_url: PublicBaseUrl | None = None
    whatsapp_access_token: ChannelSecret | None = None
    meta_app_secret: ChannelSecret | None = None
    meta_webhook_verify_token: WebhookVerificationToken | None = None
    voice_webhook_secret: WebhookVerificationToken | None = None
    manager_telegram_bot_token: ChannelSecret | None = None
