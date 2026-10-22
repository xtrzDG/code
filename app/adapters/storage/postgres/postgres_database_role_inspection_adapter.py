"""
What each pool's login role may see (migration 1200), asked of the server
at startup so a misconfigured DATABASE_URL_TENANT (the migration role, a
superuser, a member of workshop_platform) is caught before any request.
"""

import psycopg
from psycopg.rows import TupleRow

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.database_roles import DatabaseRoleInspectionAdapterContract
from app.schemas.constants.storage import DatabasePoolKind, DatabaseRoleGroup
from app.schemas.dto.database_roles import PoolRole
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_strings import DatabaseRoleName

# Waiting longer than this for a connection at startup means the database
# cannot be asked now; the check then leaves it to the readiness probe.
ACQUIRE_TIMEOUT_SECONDS: float = 5.0
# USAGE: the group's policies apply to the role. MEMBER: the role is the
# group (or the owner) or may `set role` to it, which a statement smuggled
# into a request could do as well.
POOL_ROLE_QUERY: str = """
select
    r.rolname,
    r.rolsuper,
    r.rolbypassrls,
    exists (
        select from pg_catalog.pg_roles g
        where g.rolname = %(tenant)s
          and pg_catalog.pg_has_role(r.oid, g.oid, 'USAGE')
    ),
    exists (
        select from pg_catalog.pg_roles g
        where g.rolname = %(platform)s
          and pg_catalog.pg_has_role(r.oid, g.oid, 'MEMBER')
    ),
    exists (
        select from pg_catalog.pg_class c
        join pg_catalog.pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'workshop'
          and c.relkind in ('r', 'p')
          and pg_catalog.pg_has_role(r.oid, c.relowner, 'MEMBER')
    )
from pg_catalog.pg_roles r
where r.rolname = current_user
"""


class PostgresDatabaseRoleInspectionAdapter(DatabaseRoleInspectionAdapterContract):
    def __init__(self, connection_pools: PostgresConnectionPools) -> None:
        self._connection_pools: PostgresConnectionPools = connection_pools

    def inspect_pool_roles(self) -> list[PoolRole]:
        pools: PostgresConnectionPools = self._connection_pools
        if pools.is_single:
            return [inspect_pool(pools.tenant, DatabasePoolKind.SHARED)]

        return [
            inspect_pool(pools.tenant, DatabasePoolKind.TENANT),
            inspect_pool(pools.platform, DatabasePoolKind.PLATFORM),
        ]


def inspect_pool(
    connection_pool: PostgresConnectionPoolClient, pool: DatabasePoolKind
) -> PoolRole:
    try:
        with (
            connection_pool.connection(
                acquire_timeout_seconds=ACQUIRE_TIMEOUT_SECONDS,
                joins_open_transaction=False,
            ) as connection,
            connection.transaction(),
        ):
            row: TupleRow | None = connection.execute(
                POOL_ROLE_QUERY,
                {
                    "tenant": DatabaseRoleGroup.TENANT.value,
                    "platform": DatabaseRoleGroup.PLATFORM.value,
                },
            ).fetchone()
    except psycopg.Error as error:
        raise ExternalServiceError(
            f"The {pool.value} pool's database role could not be read."
        ) from error

    if row is None:
        raise ExternalServiceError(f"The {pool.value} pool's database role is unknown.")

    return PoolRole(
        pool=pool,
        role_name=DatabaseRoleName(str(row[0])),
        is_superuser=bool(row[1]),
        bypasses_row_security=bool(row[2]),
        is_tenant_member=bool(row[3]),
        is_platform_member=bool(row[4]),
        owns_tables=bool(row[5]),
    )
