"""DATABASE_URL_TENANT, DATABASE_URL_PLATFORM, DB_PLATFORM_POOL_SIZE: the two pools."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.database_role_settings import DatabaseRoleSettings
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import DatabasePoolSize
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    parse_setting,
    read_integer,
)


class DatabaseRoleSettingsSection(TypedDict):
    """The `AppSettings` field of the two database roles."""

    database_roles: DatabaseRoleSettings


def read_database_role_settings(
    environment_variables: Mapping[str, str],
    database_url: DatabaseUrl | None,
    is_production: bool,
    default_platform_pool_size: int,
) -> DatabaseRoleSettingsSection:
    """
    Both role addresses or neither: one alone would leave a pool on the
    migration role. In production a database needs both, so the
    application never runs on a role that may see every business for
    every request.
    """

    tenant_url: DatabaseUrl | None = optional_text(
        environment_variables, "DATABASE_URL_TENANT", DatabaseUrl
    )
    platform_url: DatabaseUrl | None = optional_text(
        environment_variables, "DATABASE_URL_PLATFORM", DatabaseUrl
    )
    if (tenant_url is None) != (platform_url is None):
        raise ValidationFailedError(
            "Set both DATABASE_URL_TENANT and DATABASE_URL_PLATFORM, or neither "
            '(docs/operations/deploys.md, "Database roles").'
        )

    if tenant_url is not None and database_url is None:
        raise ValidationFailedError(
            "DATABASE_URL_TENANT and DATABASE_URL_PLATFORM need DATABASE_URL "
            "(the migration role) as well."
        )

    if is_production and database_url is not None and tenant_url is None:
        raise ValidationFailedError(
            "Production connects with two roles: set DATABASE_URL_TENANT and "
            "DATABASE_URL_PLATFORM (docs/operations/deploys.md, "
            '"Database roles").'
        )

    return DatabaseRoleSettingsSection(
        database_roles=DatabaseRoleSettings(
            tenant_url=tenant_url,
            platform_url=platform_url,
            platform_pool_size=parse_setting(
                "DB_PLATFORM_POOL_SIZE",
                read_integer(
                    environment_variables,
                    "DB_PLATFORM_POOL_SIZE",
                    default_platform_pool_size,
                ),
                DatabasePoolSize,
            ),
        )
    )


def default_platform_pool_size(db_pool_size: int) -> int:
    """
    DB_PLATFORM_POOL_SIZE when unset: a quarter of the tenant pool, at
    least two. Platform statements (sign-in, sessions, the job queue's
    claims, rate limits) are short and never wait for the model.
    """

    return max(2, db_pool_size // 4)
