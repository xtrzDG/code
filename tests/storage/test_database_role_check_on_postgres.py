"""
The startup check of the pools' database roles (migration 1200): the
application's two login roles pass; a tenant pool on the tables' owner (a
member of workshop_platform) or a platform pool on a tenant role stops
production and is a warning elsewhere; a database that cannot be asked is
left to the readiness probe.
"""

import logging

import pytest

from app.adapters.storage.postgres.postgres_database_role_inspection_adapter import (
    PostgresDatabaseRoleInspectionAdapter,
)
from app.clients.postgres.pinned_connections import PinnedConnections
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.containers.app import AppContainer
from app.gateways.startup_checks import check_database_roles
from app.schemas.constants.storage import DatabasePoolKind
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.storage.database_role_rules import find_role_problems
from tests.e2e.workshop_container import replace_provider
from tests.storage.postgres_roles import (
    PLATFORM_LOGIN_ROLE,
    TENANT_LOGIN_ROLE,
    RoleDatabase,
)
from tests.storage.postgres_server import APP_ROLE_NAME

PRODUCTION: dict[str, str] = {"APP_ENV": "production", "ENCRYPTION_KEY": "x" * 40}
LOGGER_NAME: str = "app.gateways.startup_checks"
# Nothing listens there: the database cannot be asked.
UNREACHABLE_URL: DatabaseUrl = DatabaseUrl("host=/nonexistent port=1 dbname=x user=y")


def pools_on(
    tenant_url: DatabaseUrl, platform_url: DatabaseUrl
) -> PostgresConnectionPools:
    pins = PinnedConnections()
    return PostgresConnectionPools(
        tenant=PostgresConnectionPoolClient(tenant_url, max_size=1, pins=pins),
        platform=PostgresConnectionPoolClient(platform_url, max_size=1, pins=pins),
    )


def container_with(
    pools: PostgresConnectionPools, environment: dict[str, str]
) -> AppContainer:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings(environment))
    replace_provider(
        container.adapters.database_roles, PostgresDatabaseRoleInspectionAdapter(pools)
    )
    return container


def test_the_applications_two_roles_pass(role_urls: RoleDatabase) -> None:
    pools = pools_on(role_urls.tenant_url, role_urls.platform_url)
    try:
        roles = PostgresDatabaseRoleInspectionAdapter(pools).inspect_pool_roles()
        problems = check_database_roles(container_with(pools, PRODUCTION))
    finally:
        pools.close()

    tenant, platform = roles
    assert (tenant.pool, str(tenant.role_name)) == (
        DatabasePoolKind.TENANT,
        TENANT_LOGIN_ROLE,
    )
    assert (tenant.is_tenant_member, tenant.is_platform_member) == (True, False)
    assert (tenant.is_superuser, tenant.bypasses_row_security) == (False, False)
    assert not tenant.owns_tables
    assert (platform.pool, str(platform.role_name)) == (
        DatabasePoolKind.PLATFORM,
        PLATFORM_LOGIN_ROLE,
    )
    assert platform.is_platform_member and not platform.owns_tables
    assert problems == []


def test_the_tables_owner_as_the_tenant_role_stops_production(
    role_urls: RoleDatabase,
) -> None:
    pools = pools_on(role_urls.owner_url, role_urls.tenant_url)
    try:
        roles = PostgresDatabaseRoleInspectionAdapter(pools).inspect_pool_roles()
        with pytest.raises(ValidationFailedError) as refused:
            check_database_roles(container_with(pools, PRODUCTION))
    finally:
        pools.close()

    assert [str(problem) for problem in find_role_problems(roles)] == [
        f"the tenant pool's role {APP_ROLE_NAME} is or may become workshop_platform",
        f"the tenant pool's role {APP_ROLE_NAME} owns the tables (or may become "
        "their owner)",
        f"the tenant pool's role {APP_ROLE_NAME} is not a member of workshop_tenant",
        f"the platform pool's role {TENANT_LOGIN_ROLE} is not a member of "
        "workshop_platform",
    ]
    assert "Database roles" in str(refused.value)


def test_development_warns_and_an_unreachable_database_is_left_to_readiness(
    role_urls: RoleDatabase, caplog: pytest.LogCaptureFixture
) -> None:
    misconfigured = pools_on(role_urls.owner_url, role_urls.platform_url)
    unreachable = pools_on(UNREACHABLE_URL, UNREACHABLE_URL)
    try:
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            warned = check_database_roles(container_with(misconfigured, {}))
            skipped = check_database_roles(container_with(unreachable, PRODUCTION))
    finally:
        misconfigured.close()
        unreachable.close()

    assert len(warned) == 3
    assert skipped == []
    assert "do not keep businesses apart" in caplog.text
    assert "could not be checked" in caplog.text


def test_a_shared_pool_is_developments_setup(role_urls: RoleDatabase) -> None:
    pool = PostgresConnectionPoolClient(role_urls.owner_url, max_size=1)
    try:
        roles = PostgresDatabaseRoleInspectionAdapter(
            PostgresConnectionPools.single(pool)
        ).inspect_pool_roles()
    finally:
        pool.close()

    [shared] = roles
    assert (shared.pool, str(shared.role_name)) == (
        DatabasePoolKind.SHARED,
        APP_ROLE_NAME,
    )
    assert shared.owns_tables and shared.is_platform_member
    assert find_role_problems(roles) == []
