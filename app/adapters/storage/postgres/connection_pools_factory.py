"""
Build a process's two Postgres pools for the container wiring.

With DATABASE_URL_TENANT and DATABASE_URL_PLATFORM the tenant pool (up to
DB_POOL_SIZE connections) logs in with the tenant role and the platform
pool (up to DB_PLATFORM_POOL_SIZE) with the platform role (migration
1200). Without them one pool on DATABASE_URL serves both: local
development and tests only, since production refuses to start without
the two roles (`read_database_role_settings`). Without DATABASE_URL there
is no pool at all (in-memory storage).
"""

from app.clients.postgres.pinned_connections import PinnedConnections
from app.clients.postgres.pool_instruments import NO_POOL_INSTRUMENTS, PoolInstruments
from app.clients.postgres.postgres_connection_pool_client import (
    DEFAULT_APPLICATION_NAME,
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.configurations.database_role_settings import DatabaseRoleSettings
from app.schemas.typings.platform.strings import DatabaseUrl

# A request or job statement that runs longer is cancelled by the server;
# a transaction left open longer (a stuck thread) is ended by it.
STATEMENT_TIMEOUT_SECONDS: int = 10
IDLE_IN_TRANSACTION_TIMEOUT_SECONDS: int = 30
# What pg_stat_activity shows for each pool's sessions.
TENANT_APPLICATION_NAME: str = "assistant-workshop-tenant"
PLATFORM_APPLICATION_NAME: str = "assistant-workshop-platform"
OWNER_APPLICATION_NAME: str = "assistant-workshop-maintenance"


def build_postgres_connection_pools(
    settings: AppSettings,
    instruments: PoolInstruments = NO_POOL_INSTRUMENTS,
) -> PostgresConnectionPools | None:
    """
    The process's pools when DATABASE_URL is set, otherwise None. Every
    connection gets the statement and idle-transaction timeouts above (the
    migration commands use their own, longer ones); connections idle for
    DB_POOL_MAX_IDLE_SECONDS close down to DB_POOL_MIN_SIZE. `instruments`
    measure them and trace their statements. The pools share one pin
    registry, so work inside a unit of work joins its transaction.
    """

    if settings.database_url is None:
        return None

    roles: DatabaseRoleSettings = settings.database_roles
    pins = PinnedConnections()
    if roles.tenant_url is None or roles.platform_url is None:
        return PostgresConnectionPools.single(
            build_pool(
                settings,
                settings.database_url,
                int(settings.db_pool_size),
                instruments,
                pins,
                DEFAULT_APPLICATION_NAME,
            )
        )

    return PostgresConnectionPools(
        tenant=build_pool(
            settings,
            roles.tenant_url,
            int(settings.db_pool_size),
            instruments,
            pins,
            TENANT_APPLICATION_NAME,
        ),
        platform=build_pool(
            settings,
            roles.platform_url,
            int(roles.platform_pool_size),
            instruments,
            pins,
            PLATFORM_APPLICATION_NAME,
        ),
    )


def build_pool(
    settings: AppSettings,
    database_url: DatabaseUrl,
    max_size: int,
    instruments: PoolInstruments,
    pins: PinnedConnections,
    application_name: str,
) -> PostgresConnectionPoolClient:
    return PostgresConnectionPoolClient(
        database_url=database_url,
        max_size=max_size,
        application_name=application_name,
        statement_timeout_seconds=STATEMENT_TIMEOUT_SECONDS,
        idle_in_transaction_timeout_seconds=IDLE_IN_TRANSACTION_TIMEOUT_SECONDS,
        min_size=int(settings.db_pool_min_size),
        max_idle_seconds=float(int(settings.db_pool_max_idle_seconds)),
        instruments=instruments,
        pins=pins,
    )


def build_owner_pool(settings: AppSettings) -> PostgresConnectionPoolClient | None:
    """
    One connection as the tables' owner (DATABASE_URL), for the
    maintenance commands that only the owner may run (`workshop
    purge-audit-log` calls `workshop.purge_audit_chain`). Nothing builds it
    in the API or the worker: their storage runs on the two roles' pools.
    """

    if settings.database_url is None:
        return None

    return PostgresConnectionPoolClient(
        database_url=settings.database_url,
        max_size=1,
        application_name=OWNER_APPLICATION_NAME,
    )


def application_database_url(settings: AppSettings) -> DatabaseUrl | None:
    """
    The address of the application's sessions outside the pools (the
    LISTEN connections of live events and job wake-ups): the platform
    role's, else DATABASE_URL. The application never connects as the
    migration role once the two roles are set.
    """

    return settings.database_roles.platform_url or settings.database_url


def platform_pool_of(
    connection_pools: PostgresConnectionPools | None,
) -> PostgresConnectionPoolClient | None:
    """The platform pool, for adapters of platform tables (None in memory)."""

    return None if connection_pools is None else connection_pools.platform
