"""
Production refuses to start on any unset, test or development setting, each
named by its variable; development, tests and the preview stand never ask
(docs/operations/go-live.md, "Production refuses to start").
"""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.production.production_problems import (
    find_production_problems,
    require_production_settings,
)
from tests.platform.production_settings import (
    PRODUCTION_ENVIRONMENT,
    problems_with,
    production_with,
)


def test_a_complete_production_environment_has_no_problem() -> None:
    assert problems_with({}) == []


@pytest.mark.parametrize(
    ("changes", "named"),
    [
        (
            {
                "DATABASE_URL": None,
                "DATABASE_URL_TENANT": None,
                "DATABASE_URL_PLATFORM": None,
            },
            "DATABASE_URL",
        ),
        ({"RECORDINGS_STORAGE": "local"}, "RECORDINGS_STORAGE"),
        ({"RECORDINGS_STORAGE": None}, "RECORDINGS_STORAGE"),
        ({"LOG_FORMAT": "text"}, "LOG_FORMAT"),
        ({"PLATFORM_DAILY_SPEND_BUDGET_USD": None}, "PLATFORM_DAILY_SPEND_BUDGET_USD"),
        ({"PLATFORM_DAILY_SPEND_BUDGET_USD": "0"}, "PLATFORM_DAILY_SPEND_BUDGET_USD"),
        ({"SELLER_LEGAL_NAME": None}, "SELLER_LEGAL_NAME"),
        ({"SELLER_COUNTRY_CODE": " "}, "SELLER_COUNTRY_CODE"),
        ({"SELLER_TIME_ZONE": None}, "SELLER_TIME_ZONE"),
        ({"SELLER_ADDRESS": None}, "SELLER_ADDRESS"),
        ({"TURNSTILE_SITE_KEY": None, "TURNSTILE_SECRET_KEY": None}, "TURNSTILE"),
        ({"SMTP_SECURITY": "none"}, "SMTP_SECURITY"),
    ],
)
def test_each_missing_or_unsafe_setting_is_named(
    changes: dict[str, str | None], named: str
) -> None:
    problems = problems_with(changes)

    assert len(problems) == 1, problems
    assert problems[0].startswith(named), problems


@pytest.mark.parametrize("value", [None, "   "])
def test_an_empty_encryption_key_is_refused(value: str | None) -> None:
    # Object storage refuses at once (recordings are sealed with the key);
    # without it the key is still a production problem of its own.
    with pytest.raises(ValidationFailedError, match="ENCRYPTION_KEY"):
        assemble_app_settings(production_with({"ENCRYPTION_KEY": value}))

    [*_, problem] = problems_with(
        {"ENCRYPTION_KEY": value, "RECORDINGS_STORAGE": "local"}
    )
    assert problem.startswith("ENCRYPTION_KEY is not set")


@pytest.mark.parametrize(
    "variable", ["APP_BASE_URL", "CABINET_BASE_URL", "CORS_ALLOWED_ORIGINS"]
)
def test_the_public_addresses_are_required(variable: str) -> None:
    [problem] = problems_with({variable: None})

    assert problem.startswith(f"{variable} is not set")


@pytest.mark.parametrize(
    ("variable", "address"),
    [
        ("APP_BASE_URL", "http://api.workshop.example"),
        ("CABINET_BASE_URL", "http://app.workshop.example"),
        ("CORS_ALLOWED_ORIGINS", "https://app.workshop.example,http://evil.example"),
        ("OPENAI_BASE_URL", "http://eu.api.openai.com/v1"),
        ("LANGFUSE_HOST", "http://cloud.langfuse.com"),
        ("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otlp.example.com"),
        ("RECORDINGS_S3_ENDPOINT_URL", "http://s3.eu-central-1.amazonaws.com"),
    ],
)
def test_plain_http_addresses_are_refused(variable: str, address: str) -> None:
    [problem] = problems_with({variable: address})

    assert problem.startswith(f"{variable} must be an https address")


@pytest.mark.parametrize(
    "address",
    [
        "https://localhost:8000",
        "https://127.0.0.1",
        "https://[::1]:8443",
        "https://0.0.0.0",
        "https://api.localhost",
        "https://LocalHost.:8443",
        "https://[::ffff:127.0.0.1]",
    ],
)
def test_this_machine_never_serves_production(address: str) -> None:
    [problem] = problems_with({"APP_BASE_URL": address})

    assert problem.startswith("APP_BASE_URL points at this machine")


@pytest.mark.parametrize(
    ("site_key", "secret_key", "named"),
    [
        (
            "1x00000000000000000000AA",
            "0x4AAAAAAAfake-live-secret",
            "TURNSTILE_SITE_KEY",
        ),
        (
            "0x4AAAAAAABkMYinukE8nzY",
            "2x0000000000000000000000000000000AA",
            "TURNSTILE_SECRET_KEY",
        ),
        (
            "3x00000000000000000000FF",
            "0x4AAAAAAAfake-live-secret",
            "TURNSTILE_SITE_KEY",
        ),
    ],
)
def test_cloudflares_test_keys_are_refused(
    site_key: str, secret_key: str, named: str
) -> None:
    [problem] = problems_with(
        {"TURNSTILE_SITE_KEY": site_key, "TURNSTILE_SECRET_KEY": secret_key}
    )

    assert problem.startswith(f"{named} is one of Cloudflare's test keys")


@pytest.mark.parametrize("written_out", ["Assistant Workshop", " assistant workshop "])
def test_the_development_seller_name_written_out_is_refused(written_out: str) -> None:
    # A copied .env.example names the placeholder: still no company.
    [problem] = problems_with({"SELLER_LEGAL_NAME": written_out})

    assert problem.startswith(
        'SELLER_LEGAL_NAME is the development placeholder "Assistant Workshop"'
    )
    assert problems_with({"SELLER_LEGAL_NAME": "Assistant Workshop S.r.l."}) == []


def test_every_problem_is_reported_at_once_and_names_no_secret() -> None:
    settings = assemble_app_settings(
        production_with(
            {
                "DATABASE_URL": None,
                "DATABASE_URL_TENANT": None,
                "DATABASE_URL_PLATFORM": None,
                "LOG_FORMAT": "text",
                "TURNSTILE_SECRET_KEY": "1x0000000000000000000000000000000AA",
            }
        )
    )
    problems = find_production_problems(settings)

    with pytest.raises(ValidationFailedError) as refused:
        require_production_settings(settings, problems)

    message: str = str(refused.value)
    assert message.startswith("Production refuses to start (APP_ENV=production):")
    for variable in ("DATABASE_URL", "LOG_FORMAT", "TURNSTILE_SECRET_KEY"):
        assert f"\n- {variable}" in message
    assert "1x0000000000000000000000000000000AA" not in message
    assert PRODUCTION_ENVIRONMENT["OPENAI_API_KEY"] not in message


@pytest.mark.parametrize("environment", ["development", "test"])
def test_development_and_tests_are_never_asked(environment: str) -> None:
    # The settings of a local run: in memory, http, the scripted model,
    # text logs, no Turnstile, no budget, no seller.
    settings = assemble_app_settings(
        {
            "APP_ENV": environment,
            "APP_BASE_URL": "http://localhost:8000",
            "CORS_ALLOWED_ORIGINS": "http://localhost:3000",
            "LLM_PROVIDER": "scripted",
            "SMTP_SECURITY": "none",
            "LOG_FORMAT": "text",
        }
    )
    problems = find_production_problems(settings)

    assert problems != []
    require_production_settings(settings, problems)
    assert [str(name) for name in settings.development_default_variables] == [
        "SELLER_LEGAL_NAME",
        "SELLER_COUNTRY_CODE",
        "SELLER_TIME_ZONE",
    ]
    assert (str(settings.seller.country_code), str(settings.seller.time_zone)) == (
        "IT",
        "Europe/Rome",
    )
