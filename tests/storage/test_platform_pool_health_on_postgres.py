"""
A broken platform pool (an unreachable or wrong DATABASE_URL_PLATFORM)
is caught twice: the readiness probe asks both pools, so the instance is
not ready, and production refuses to start when a pool's role cannot be
checked at all.
"""

import pytest

from app.adapters.health.database_probe_factory import build_database_probe_adapter
from app.adapters.storage.postgres.postgres_database_role_inspection_adapter import (
    PostgresDatabaseRoleInspectionAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.clients.postgres.pinned_connections import PinnedConnections
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.containers.app import AppContainer
from app.gateways.startup_checks import check_database_roles
from app.schemas.constants.observability import (
    DatabaseProbeFailure,
    HealthCheckStatus,
    ReadinessState,
)
from app.schemas.dto.health import ReadinessQuery
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.use_cases.observability.check_readiness_use_case import (
    CheckReadinessUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.observability.readiness_memory import ReadinessMemory
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.data_tasks.data_task_support import data_task_states, no_data_tasks
from tests.e2e.workshop_container import replace_provider
from tests.storage.postgres_roles import RoleDatabase
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY, build_fixed_wall_clock
from tests.storage.test_readiness_postgres import EmptyHeartbeats

PRODUCTION: dict[str, str] = {"APP_ENV": "production", "ENCRYPTION_KEY": "x" * 40}
# Nothing listens there: the platform role cannot be reached.
UNREACHABLE_URL: DatabaseUrl = DatabaseUrl("postgresql://workshop@127.0.0.1:1/workshop")


def pools_on(
    tenant_url: DatabaseUrl, platform_url: DatabaseUrl
) -> PostgresConnectionPools:
    pins = PinnedConnections()
    return PostgresConnectionPools(
        tenant=PostgresConnectionPoolClient(tenant_url, max_size=2, pins=pins),
        platform=PostgresConnectionPoolClient(platform_url, max_size=2, pins=pins),
    )


def readiness(pools: PostgresConnectionPools) -> CheckReadinessUseCase:
    return CheckReadinessUseCase(
        database_probe=build_database_probe_adapter(pools),
        migration_source=SqlFileMigrationSourceAdapter(MIGRATIONS_DIRECTORY),
        worker_heartbeat_repo=EmptyHeartbeats(),
        storage_scope=StorageScopeContext(),
        wall_clock=build_fixed_wall_clock(),
        memory=ReadinessMemory(),
        data_task_registry=no_data_tasks(),
        data_task_state_repo=data_task_states(),
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


def test_both_role_pools_answering_are_ready(role_urls: RoleDatabase) -> None:
    pools = pools_on(role_urls.tenant_url, role_urls.platform_url)
    try:
        report = readiness(pools).run(ReadinessQuery())
    finally:
        pools.close()

    assert report.checks.database.status is HealthCheckStatus.OK
    assert report.checks.migrations.status is HealthCheckStatus.OK
    assert report.status is ReadinessState.READY


def test_an_unreachable_platform_pool_is_not_ready(role_urls: RoleDatabase) -> None:
    pools = pools_on(role_urls.tenant_url, UNREACHABLE_URL)
    try:
        probe = build_database_probe_adapter(pools).probe()
        report = readiness(pools).run(ReadinessQuery())
    finally:
        pools.close()

    assert probe.status is HealthCheckStatus.FAILED
    assert probe.failure is DatabaseProbeFailure.UNREACHABLE
    assert report.status is ReadinessState.NOT_READY


def test_production_refuses_to_start_with_an_unreachable_platform_pool(
    role_urls: RoleDatabase,
) -> None:
    pools = pools_on(role_urls.tenant_url, UNREACHABLE_URL)
    try:
        with pytest.raises(ValidationFailedError, match="could not be checked"):
            check_database_roles(container_with(pools, PRODUCTION))
        development = check_database_roles(container_with(pools, {}))
    finally:
        pools.close()

    assert development == []
