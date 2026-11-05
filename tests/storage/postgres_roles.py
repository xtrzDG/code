"""
The application's two database roles on the throwaway test server, as an
administrator sets them up in production (docs/operations/deploys.md,
"Database roles").

The migration role (`workshop_app`, the tables' owner) creates the groups
`workshop_tenant` and `workshop_platform` when the first database runs
migration 1200; the login roles below then join them, once per server:

    workshop_tenant_login    the tenant pool's role: one business at a time
    workshop_platform_login  the platform pool's role: every business

Both are neither superuser nor BYPASSRLS and own nothing, exactly like the
login roles of DATABASE_URL_TENANT and DATABASE_URL_PLATFORM.
"""

from dataclasses import dataclass

from psycopg import sql

from app.adapters.locks.postgres_advisory_lock_adapter import (
    PostgresAdvisoryLockAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.pinned_connections import PinnedConnections
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.storage import StorageScopeContract
from app.schemas.typings.platform.strings import DatabaseUrl
from tests.storage.postgres_server import ThrowawayPostgresServer

TENANT_GROUP: str = "workshop_tenant"
PLATFORM_GROUP: str = "workshop_platform"
TENANT_LOGIN_ROLE: str = "workshop_tenant_login"
PLATFORM_LOGIN_ROLE: str = "workshop_platform_login"
LOGIN_ROLES: tuple[tuple[str, str], ...] = (
    (TENANT_LOGIN_ROLE, TENANT_GROUP),
    (PLATFORM_LOGIN_ROLE, PLATFORM_GROUP),
)
DEFAULT_TEST_POOL_SIZE: int = 8


def ensure_login_roles(server: ThrowawayPostgresServer) -> None:
    """Create the two login roles in their groups (idempotent, as admin)."""

    with server.admin_connection() as connection:
        for login_role, group in LOGIN_ROLES:
            exists = connection.execute(
                "select 1 from pg_roles where rolname = %s", (login_role,)
            ).fetchone()
            if exists is None:
                connection.execute(
                    sql.SQL(
                        "create role {} login nosuperuser nobypassrls in role {}"
                    ).format(sql.Identifier(login_role), sql.Identifier(group))
                )


@dataclass(frozen=True)
class RoleDatabase:
    """One test database's addresses: its owner's and the two roles'."""

    owner_url: DatabaseUrl
    tenant_url: DatabaseUrl
    platform_url: DatabaseUrl

    def pools(
        self,
        max_size: int = DEFAULT_TEST_POOL_SIZE,
        statement_timeout_seconds: int | None = None,
    ) -> PostgresConnectionPools:
        """The tenant and the platform pool, as one process has them."""

        pins = PinnedConnections()
        return PostgresConnectionPools(
            tenant=PostgresConnectionPoolClient(
                self.tenant_url,
                max_size=max_size,
                statement_timeout_seconds=statement_timeout_seconds,
                pins=pins,
            ),
            platform=PostgresConnectionPoolClient(
                self.platform_url,
                max_size=max_size,
                statement_timeout_seconds=statement_timeout_seconds,
                pins=pins,
            ),
        )

    def environment(self) -> dict[str, str]:
        """The three addresses a process of the application reads."""

        return {
            "DATABASE_URL": str(self.owner_url),
            "DATABASE_URL_TENANT": str(self.tenant_url),
            "DATABASE_URL_PLATFORM": str(self.platform_url),
        }


def role_database(server: ThrowawayPostgresServer, database_name: str) -> RoleDatabase:
    return RoleDatabase(
        owner_url=server.app_database_url(database_name),
        tenant_url=DatabaseUrl(server.conninfo(database_name, TENANT_LOGIN_ROLE)),
        platform_url=DatabaseUrl(server.conninfo(database_name, PLATFORM_LOGIN_ROLE)),
    )


def advisory_locks_on(
    connection_pools: PostgresConnectionPools, storage_scope: StorageScopeContract
) -> PostgresAdvisoryLockAdapter:
    """The advisory locks of a process with these pools and scope."""

    return PostgresAdvisoryLockAdapter(
        connection_pools=connection_pools,
        storage_scope=storage_scope,
        unit_of_work=PostgresUnitOfWorkAdapter(connection_pools, storage_scope),
    )
