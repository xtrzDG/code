import pytest

from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings


def test_defaults_are_safe_for_development() -> None:
    settings = assemble_app_settings({})

    assert settings.environment is DeploymentEnvironment.DEVELOPMENT
    assert settings.llm_model_id == "claude-opus-5-5"
    assert settings.llm_chat_effort is LlmEffort.LOW
    assert settings.is_otp_code_logging_enabled is True
    assert CountryCode("KP") in settings.restricted_country_codes
    assert settings.public_base_url is None


def test_production_disables_code_logging_and_reads_overrides() -> None:
    settings = assemble_app_settings(
        {
            "APP_ENV": "production",
            "LLM_MODEL_ID": "claude-sonnet-5-5",
            "RESTRICTED_COUNTRY_CODES": "",
            "PUBLIC_BASE_URL": "https://api.example.com",
        }
    )

    assert settings.is_otp_code_logging_enabled is False
    assert settings.llm_model_id == "claude-sonnet-5-5"
    assert settings.restricted_country_codes == []
    assert settings.public_base_url == "https://api.example.com"


def test_invalid_integer_is_reported_with_variable_name() -> None:
    with pytest.raises(ValidationFailedError, match="LLM_TOOL_ROUND_LIMIT"):
        assemble_app_settings({"LLM_TOOL_ROUND_LIMIT": "many"})
