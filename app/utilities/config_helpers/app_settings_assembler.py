"""Assemble AppSettings from environment variables (the external boundary)."""

import os
from collections.abc import Mapping

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import DataRegion
from app.schemas.exceptions.application_errors import ValidationFailedError
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

DEFAULT_LLM_MODEL_ID: str = "claude-opus-5-5"
# Comprehensively sanctioned jurisdictions for a US-person founder.
# Confirm the list with a lawyer before launch; override with
# RESTRICTED_COUNTRY_CODES (comma-separated, empty string disables).
DEFAULT_RESTRICTED_COUNTRY_CODES: str = "CU,IR,KP,SY"
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

    return AppSettings(
        environment=environment,
        llm_model_id=LlmModelId(
            read_text(environment_variables, "LLM_MODEL_ID", DEFAULT_LLM_MODEL_ID)
        ),
        llm_judge_model_id=LlmModelId(
            read_text(
                environment_variables,
                "LLM_JUDGE_MODEL_ID",
                DEFAULT_LLM_MODEL_ID,
            )
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
            read_boolean(environment_variables, "OTP_LOG_CODES", is_development)
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
        public_base_url=optional_text(
            environment_variables,
            "PUBLIC_BASE_URL",
            PublicBaseUrl,
        ),
        whatsapp_access_token=optional_text(
            environment_variables,
            "WHATSAPP_ACCESS_TOKEN",
            ChannelSecret,
        ),
        meta_app_secret=optional_text(
            environment_variables,
            "META_APP_SECRET",
            ChannelSecret,
        ),
        meta_webhook_verify_token=optional_text(
            environment_variables,
            "META_WEBHOOK_VERIFY_TOKEN",
            WebhookVerificationToken,
        ),
        voice_webhook_secret=optional_text(
            environment_variables,
            "VOICE_WEBHOOK_SECRET",
            WebhookVerificationToken,
        ),
        manager_telegram_bot_token=optional_text(
            environment_variables,
            "MANAGER_TELEGRAM_BOT_TOKEN",
            ChannelSecret,
        ),
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


def optional_text[TypedText: str](
    environment_variables: Mapping[str, str],
    variable_name: str,
    typed_text_type: type[TypedText],
) -> TypedText | None:
    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return None

    return typed_text_type(raw_value)
