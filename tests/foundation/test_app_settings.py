import pytest

from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.config_helpers.app_settings.app_settings_assembler import assemble_app_settings


def test_defaults_follow_the_concept_stack() -> None:
    settings = assemble_app_settings({})

    assert settings.environment is DeploymentEnvironment.DEVELOPMENT
    assert settings.llm_provider is LlmProvider.OPENAI
    assert settings.llm_model_id == "gpt-5-mini"
    assert settings.openai_base_url == "https://eu.api.openai.com/v1"
    assert settings.llm_chat_effort is LlmEffort.LOW
    assert settings.is_otp_code_logging_enabled is True
    assert settings.default_recording_retention_days == 90
    assert CountryCode("KP") in settings.restricted_country_codes
    assert settings.app_base_url is None


def test_provider_switch_changes_the_default_model() -> None:
    settings = assemble_app_settings({"LLM_PROVIDER": "anthropic"})

    assert settings.llm_provider is LlmProvider.ANTHROPIC
    assert settings.llm_model_id == "claude-opus-5-5"


def test_production_disables_code_logging_and_reads_concept_variables() -> None:
    settings = assemble_app_settings(
        {
            "APP_ENV": "production",
            "APP_BASE_URL": "https://api.example.com",
            "RESTRICTED_COUNTRY_CODES": "",
            "TELEGRAM_PLATFORM_BOT_TOKEN": "123:abc",
            "META_VERIFY_TOKEN": "verify-me",
        }
    )

    assert settings.is_otp_code_logging_enabled is False
    assert settings.restricted_country_codes == []
    assert settings.app_base_url == "https://api.example.com"
    assert settings.telegram_platform_bot_token == "123:abc"
    assert settings.meta_verify_token == "verify-me"


def test_invalid_integer_is_reported_with_variable_name() -> None:
    with pytest.raises(ValidationFailedError, match="LLM_TOOL_ROUND_LIMIT"):
        assemble_app_settings({"LLM_TOOL_ROUND_LIMIT": "many"})


def test_cabinet_address_defaults_to_the_development_server() -> None:
    development = assemble_app_settings({})
    configured = assemble_app_settings(
        {"APP_ENV": "production", "CABINET_BASE_URL": " https://app.example.com/ "}
    )
    production = assemble_app_settings({"APP_ENV": "production"})

    assert development.cabinet_base_url == "http://localhost:3000"
    assert configured.cabinet_base_url == "https://app.example.com"
    assert production.cabinet_base_url is None
    with pytest.raises(ValueError, match="CabinetBaseUrl"):
        assemble_app_settings({"CABINET_BASE_URL": "cabinet.example.com"})


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({}, True),
        ({"EMBEDDED_WORKER": "auto"}, True),
        ({"DATABASE_URL": "postgresql://localhost/workshop"}, False),
        ({"APP_ENV": "test"}, False),
        ({"APP_ENV": "production"}, False),
        ({"EMBEDDED_WORKER": "false"}, False),
        ({"EMBEDDED_WORKER": "TRUE", "APP_ENV": "test"}, True),
        (
            {
                "EMBEDDED_WORKER": "true",
                "DATABASE_URL": "postgresql://localhost/workshop",
            },
            True,
        ),
    ],
)
def test_embedded_worker_runs_by_default_only_over_in_memory_development_data(
    environment: dict[str, str],
    expected: bool,
) -> None:
    settings = assemble_app_settings(environment)

    assert settings.is_embedded_worker_enabled is expected


def test_embedded_worker_is_refused_in_production_and_for_unknown_values() -> None:
    with pytest.raises(ValidationFailedError, match="workshop worker"):
        assemble_app_settings({"APP_ENV": "production", "EMBEDDED_WORKER": "true"})

    with pytest.raises(ValidationFailedError, match="auto, true or false"):
        assemble_app_settings({"EMBEDDED_WORKER": "sometimes"})
