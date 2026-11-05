"""
Settings refuse nonsense in every environment, each refusal naming its
variable: an unknown APP_ENV (and an unset one on Render), "*" as a CORS
origin, timeouts and limits outside their range. A blank list variable is
unset, `none` empties it. Development keeps starting with its defaults.
"""

import pytest

from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.app_settings.compliance_settings_section import (
    DEFAULT_RESTRICTED_COUNTRY_CODES,
)
from tests.platform.production_settings import PRODUCTION_ENVIRONMENT

ENVIRONMENTS: tuple[dict[str, str], ...] = (
    {"APP_ENV": "development"},
    PRODUCTION_ENVIRONMENT,
)


@pytest.mark.parametrize("value", ["prod", "staging", "dev", "production!"])
def test_an_unknown_app_env_refuses_to_start(value: str) -> None:
    with pytest.raises(ValidationFailedError, match="APP_ENV must be one of"):
        assemble_app_settings({"APP_ENV": value})


def test_app_env_is_read_case_insensitively_and_defaults_to_development() -> None:
    assert assemble_app_settings({"APP_ENV": " Production "}).environment is (
        DeploymentEnvironment.PRODUCTION
    )
    assert assemble_app_settings({}).environment is DeploymentEnvironment.DEVELOPMENT
    assert assemble_app_settings({"RENDER": ""}).environment is (
        DeploymentEnvironment.DEVELOPMENT
    )


def test_render_without_app_env_refuses_to_start() -> None:
    with pytest.raises(ValidationFailedError, match="APP_ENV is not set"):
        assemble_app_settings({"RENDER": "true"})

    explicit = assemble_app_settings({"RENDER": "true", "APP_ENV": "development"})
    assert explicit.environment is DeploymentEnvironment.DEVELOPMENT


@pytest.mark.parametrize("environment", ENVIRONMENTS)
@pytest.mark.parametrize("origins", ["*", "https://app.workshop.example, *"])
def test_any_origin_is_refused_for_cors(
    environment: dict[str, str], origins: str
) -> None:
    with pytest.raises(
        ValidationFailedError, match='CORS_ALLOWED_ORIGINS cannot be "\\*"'
    ):
        assemble_app_settings({**environment, "CORS_ALLOWED_ORIGINS": origins})


@pytest.mark.parametrize("environment", ENVIRONMENTS)
@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("LLM_CALL_TIMEOUT_SECONDS", "0"),
        ("LLM_CALL_TIMEOUT_SECONDS", "-1"),
        ("CHAT_TURN_DEADLINE_SECONDS", "-1"),
        ("OTP_LIFETIME_SECONDS", "0"),
        ("SESSION_LIFETIME_SECONDS", "-1"),
        ("SESSION_IDLE_TIMEOUT_SECONDS", "0"),
        ("WORKER_POLL_SECONDS", "0"),
        ("OTP_SENDS_PER_HOUR", "0"),
        ("OTP_SENDS_PER_IP_PER_HOUR", "0"),
        ("OTP_VERIFIES_PER_IP_PER_10_MINUTES", "0"),
        ("API_REQUESTS_PER_IP_PER_MINUTE", "0"),
        ("PUBLIC_API_REQUESTS_PER_MINUTE", "0"),
        ("CONTACT_MESSAGE_LIMIT_PER_HOUR", "-5"),
        ("LLM_MAX_CONCURRENCY", "0"),
        ("LLM_TOOL_ROUND_LIMIT", "0"),
        ("PLATFORM_DAILY_SPEND_BUDGET_USD", "-1"),
        ("LLM_PROVIDER", "openai-ish"),
        ("SMTP_SECURITY", "tls"),
        ("LLM_CHAT_EFFORT", "maximal"),
        ("DEFAULT_DATA_REGION", "mars"),
        ("OPENAI_BASE_URL", "eu.api.openai.com"),
        ("LANGFUSE_HOST", "cloud"),
        ("CORS_ALLOWED_ORIGINS", "app.workshop.example"),
    ],
)
def test_a_value_out_of_its_range_names_its_variable(
    environment: dict[str, str], variable: str, value: str
) -> None:
    with pytest.raises(ValidationFailedError, match=variable):
        assemble_app_settings({**environment, variable: value})


@pytest.mark.parametrize("blank", ["", "   ", " , "])
def test_a_blank_list_variable_is_unset(blank: str) -> None:
    defaults = assemble_app_settings({})
    settings = assemble_app_settings(
        {
            "OTP_HIGH_RISK_COUNTRIES": blank,
            "RESTRICTED_COUNTRY_CODES": blank,
            "WHATSAPP_OTP_TEMPLATE_LANGUAGES": blank,
            "CORS_ALLOWED_ORIGINS": blank,
            "PLATFORM_ADMIN_EMAILS": blank,
        }
    )

    assert settings.otp_high_risk_country_codes == (
        defaults.otp_high_risk_country_codes
    )
    assert CountryCode("TV") in settings.otp_high_risk_country_codes
    assert [str(code) for code in settings.restricted_country_codes] == (
        DEFAULT_RESTRICTED_COUNTRY_CODES.split(",")
    )
    assert [str(code) for code in settings.whatsapp_otp_template_languages] == ["en"]
    assert settings.cors_allowed_origins == []
    assert settings.platform_admin_emails == []


def test_none_empties_a_list_with_a_default() -> None:
    settings = assemble_app_settings(
        {"OTP_HIGH_RISK_COUNTRIES": "None", "RESTRICTED_COUNTRY_CODES": " none "}
    )

    assert settings.otp_high_risk_country_codes == []
    assert settings.restricted_country_codes == []


def test_development_starts_with_its_defaults() -> None:
    settings = assemble_app_settings({})

    assert settings.environment is DeploymentEnvironment.DEVELOPMENT
    assert settings.database_url is None
    assert str(settings.seller.country_code) == "IT"
    assert int(settings.llm_call_timeout_seconds) == 25
    assert int(settings.otp_sends_per_hour) == 300
