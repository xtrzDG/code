"""
The two connection pools of a process: the tenant pool, whose role row-level
security binds to one business, and the platform pool, whose role sees
every business (migration 1200).
"""

from dataclasses import dataclass
from typing import Self

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.client_contract import ClientContract
from app.schemas.constants.storage import StorageScopeKind
from app.schemas.dto.storage import StorageScope


@dataclass(frozen=True)
class PostgresConnectionPools(ClientContract):
    """
    Storage picks the pool by the scope of each operation: a business
    scope borrows from `tenant` (DATABASE_URL_TENANT, a member of
    workshop_tenant, which sees only the rows of the business in
    app.business_id however a session changes its settings), the platform
    scope and code that entered no scope (sign-in, the user's own account:
    platform collections only, tenant ones refuse it) from `platform`
    (DATABASE_URL_PLATFORM, a member of workshop_platform). Inside a unit of work every operation joins the
    unit's transaction on the pool the unit started on
    (`pinned_connections`), so a business's transaction never sees past its
    business, even where code inside it asks for the platform scope.

    Both pools share one pin registry. Without the two role URLs (local
    development, tests of single components) both are the same pool on
    DATABASE_URL; the database role decides what it sees.
    """

    tenant: PostgresConnectionPoolClient
    platform: PostgresConnectionPoolClient

    @classmethod
    def single(cls, pool: PostgresConnectionPoolClient) -> Self:
        """One pool for both scopes (one database role)."""

        return cls(tenant=pool, platform=pool)

    @property
    def is_single(self) -> bool:
        return self.tenant is self.platform

    def for_scope(self, scope: StorageScope) -> PostgresConnectionPoolClient:
        """The pool of an operation in `scope`."""

        if scope.kind is StorageScopeKind.BUSINESS:
            return self.tenant

        return self.platform

    def is_pinned(self) -> bool:
        """Whether this thread runs inside a pin of either pool."""

        return self.tenant.is_pinned() or self.platform.is_pinned()

    def close(self) -> None:
        self.tenant.close()
        if not self.is_single:
            self.platform.close()
