"""
Every Render service that connects to the database starts with production
settings: since migration 1200 production refuses a process with
DATABASE_URL but without the two role addresses, whatever that process
does with them (the nightly backup dumps as the migration role).
"""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.config_helpers.app_settings.database_role_settings_section import (
    read_database_role_settings,
)
from tests.platform.deployment_variables import render_services

DATABASE_URL_VARIABLES: tuple[str, ...] = (
    "DATABASE_URL",
    "DATABASE_URL_TENANT",
    "DATABASE_URL_PLATFORM",
)
PLACEHOLDER_URL: str = "postgresql://role:test-password-0000@db:5432/workshop"
DEFAULT_PLATFORM_POOL_SIZE: int = 2


def database_services(blueprint_path: str) -> dict[str, set[str]]:
    """The services of a blueprint that set DATABASE_URL."""

    return {
        name: variables
        for name, variables in render_services(blueprint_path).items()
        if "DATABASE_URL" in variables
    }


def production_environment(variables: set[str]) -> dict[str, str]:
    """A placeholder address for each database variable the service sets."""

    return {
        name: PLACEHOLDER_URL for name in DATABASE_URL_VARIABLES if name in variables
    }


@pytest.mark.parametrize("blueprint_path", ["render.yaml", "render.staging.yaml"])
def test_every_database_service_passes_the_production_role_rule(
    blueprint_path: str,
) -> None:
    services: dict[str, set[str]] = database_services(blueprint_path)

    assert services, blueprint_path
    for name, variables in services.items():
        assert "APP_ENV" in variables, name
        settings = read_database_role_settings(
            production_environment(variables),
            DatabaseUrl(PLACEHOLDER_URL),
            True,
            DEFAULT_PLATFORM_POOL_SIZE,
        )
        assert settings["database_roles"].tenant_url is not None, name


def test_the_backup_cron_is_one_of_the_checked_services() -> None:
    assert "workshop-backup" in database_services("render.yaml")


def test_a_service_without_the_role_addresses_is_refused_in_production() -> None:
    with pytest.raises(ValidationFailedError, match="two roles"):
        read_database_role_settings(
            production_environment({"DATABASE_URL"}),
            DatabaseUrl(PLACEHOLDER_URL),
            True,
            DEFAULT_PLATFORM_POOL_SIZE,
        )
