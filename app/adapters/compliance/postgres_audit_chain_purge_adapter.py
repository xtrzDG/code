from typing import LiteralString

from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.platform_transaction import platform_transaction
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.audit_chain_purges import AuditChainPurgeAdapterContract
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainEntryCount,
    AuditPurgeBatchSize,
)
from app.schemas.typings.compliance.constrained_strings import AuditChainKey

PURGE_STATEMENT: LiteralString = "select workshop.purge_audit_chain(%s, %s, %s)"
AUDIT_TABLE: str = "audit_log_entries"


class PostgresAuditChainPurgeAdapter(AuditChainPurgeAdapterContract):
    """
    One call of `workshop.purge_audit_chain` (migration 1193) in one
    platform-wide transaction. The function runs with its owner's rights:
    the application's role cannot delete audit entries any other way.
    """

    def __init__(self, connection_pool: PostgresConnectionPoolClient) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool

    def purge(
        self,
        chain_key: AuditChainKey,
        created_before: Microseconds,
        max_entries: AuditPurgeBatchSize,
    ) -> AuditChainEntryCount:
        with platform_transaction(self._connection_pool, AUDIT_TABLE) as connection:
            row: TupleRow | None = connection.execute(
                PURGE_STATEMENT,
                (str(chain_key), int(created_before), int(max_entries)),
            ).fetchone()

        removed: object = None if row is None else row[0]
        return AuditChainEntryCount(removed if isinstance(removed, int) else 0)
