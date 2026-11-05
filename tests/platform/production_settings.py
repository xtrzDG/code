"""
A complete production environment (every requirement met, fake values) and
helpers that change one setting of it, for the tests of
`check_production_requirements`.
"""

from collections.abc import Mapping

from app.containers.app import AppContainer
from app.schemas.configurations.app_settings import AppSettings
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.production.production_problems import (
    find_production_problems,
)
from tests.e2e.workshop_container import replace_provider

API_ADDRESS: str = "https://api.workshop.example"
CABINET_ADDRESS: str = "https://app.workshop.example"
PRODUCTION_ENVIRONMENT: dict[str, str] = {
    "APP_ENV": "production",
    "APP_BASE_URL": API_ADDRESS,
    "CABINET_BASE_URL": CABINET_ADDRESS,
    "CORS_ALLOWED_ORIGINS": CABINET_ADDRESS,
    "DATABASE_URL": "postgresql://workshop:fake@db.internal:5432/workshop",
    "DATABASE_URL_TENANT": "postgresql://tenant:fake@db.internal:5432/workshop",
    "DATABASE_URL_PLATFORM": "postgresql://platform:fake@db.internal:5432/workshop",
    # libpq's default sslmode for the dotted (external) addresses above.
    "PGSSLMODE": "require",
    "ENCRYPTION_KEY": "a-production-test-key-of-forty-characters",
    "LLM_PROVIDER": "openai",
    "OPENAI_API_KEY": "openai-fake-key",
    "TURNSTILE_SITE_KEY": "0x4AAAAAAABkMYinukE8nzY",
    "TURNSTILE_SECRET_KEY": "0x4AAAAAAAfake-live-secret",
    "SMTP_HOST": "smtp.workshop.example",
    "SMTP_FROM": "no-reply@workshop.example",
    "RECORDINGS_STORAGE": "s3",
    "RECORDINGS_S3_ENDPOINT_URL": "https://s3.eu-central-1.amazonaws.com",
    "RECORDINGS_S3_REGION": "eu-central-1",
    "RECORDINGS_S3_BUCKET": "workshop-recordings",
    "RECORDINGS_S3_ACCESS_KEY_ID": "fake-access-key-id",
    "RECORDINGS_S3_SECRET_ACCESS_KEY": "fake-secret-access-key",
    "PLATFORM_DAILY_SPEND_BUDGET_USD": "50",
    "SELLER_LEGAL_NAME": "Workshop Italia S.r.l.",
    "SELLER_ADDRESS": "Via Roma 1\\n00184 Roma",
    "SELLER_COUNTRY_CODE": "IT",
    "SELLER_TIME_ZONE": "Europe/Rome",
}


def production_with(
    changes: Mapping[str, str | None],
    base: Mapping[str, str] = PRODUCTION_ENVIRONMENT,
) -> dict[str, str]:
    """The environment with `changes` applied (None removes a variable)."""

    environment: dict[str, str] = dict(base)
    for name, value in changes.items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    return environment


def problems_with(changes: Mapping[str, str | None]) -> list[str]:
    """What production refuses once `changes` are applied."""

    settings: AppSettings = assemble_app_settings(production_with(changes))
    return [str(problem) for problem in find_production_problems(settings)]


def container_with(environment: Mapping[str, str]) -> AppContainer:
    """An application container on these settings (nothing connects yet)."""

    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings(environment))
    return container
