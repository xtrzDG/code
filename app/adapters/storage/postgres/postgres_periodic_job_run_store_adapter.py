from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.periodic_job_run_records import (
    PeriodicJobRunRecords,
    periodic_run_key,
)
from app.adapters.storage.postgres.periodic_job_run_queries import (
    DELETE_STARTED_BEFORE,
    PERIODIC_JOB_RUNS_COLLECTION,
    SELECT_RUN,
    TRY_JOB_LOCK,
    UPSERT_RUN,
)
from app.adapters.storage.postgres.platform_transaction import (
    platform_transaction,
    read_document_text,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.jobs import (
    PeriodicJobRunStoreAdapterContract,
    PeriodicRunDecision,
)
from app.schemas.domain.jobs import PeriodicJobRunDocument
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import JobName, JobPeriodKey


class PostgresPeriodicJobRunStoreAdapter(
    PeriodicJobRunRecords,
    PeriodicJobRunStoreAdapterContract,
):
    """
    Periodic job runs on `workshop.periodic_job_runs`, one row per job and
    period. A start is decided in one transaction under
    `pg_try_advisory_xact_lock` of the job name: the worker that gets the
    lock reads the period's run, decides, and writes it before the lock
    ends; a worker that does not get it skips the job this tick. Heartbeats
    and finishing go through the document collection (row lock and token
    check).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PeriodicJobRunDocument],
        connection_pool: PostgresConnectionPoolClient,
    ) -> None:
        super().__init__(collection)
        self._connection_pool: PostgresConnectionPoolClient = connection_pool

    def claim(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
        decide: PeriodicRunDecision,
    ) -> PeriodicJobRunDocument | None:
        document_key: str = periodic_run_key(job_name, period_key)
        with platform_transaction(
            self._connection_pool, PERIODIC_JOB_RUNS_COLLECTION
        ) as connection:
            lock_row: TupleRow | None = connection.execute(
                TRY_JOB_LOCK, (str(job_name),)
            ).fetchone()
            if lock_row is None or lock_row[0] is not True:
                return None

            row: TupleRow | None = connection.execute(
                SELECT_RUN, (document_key,)
            ).fetchone()
            stored: PeriodicJobRunDocument | None = (
                None
                if row is None
                else PeriodicJobRunDocument.model_validate_json(
                    read_document_text(row, PERIODIC_JOB_RUNS_COLLECTION)
                )
            )
            decided: PeriodicJobRunDocument | None = decide(stored)
            if decided is None:
                return None

            serialized_run: str = decided.model_dump_json()
            connection.execute(
                UPSERT_RUN,
                (
                    document_key,
                    serialized_run,
                    int(decided.created_at),
                    int(decided.updated_at),
                ),
            )

        return PeriodicJobRunDocument.model_validate_json(serialized_run)

    def purge_started_before(self, started_before: Microseconds) -> ProcessedItemCount:
        with platform_transaction(
            self._connection_pool, PERIODIC_JOB_RUNS_COLLECTION
        ) as connection:
            deleted: int = connection.execute(
                DELETE_STARTED_BEFORE, (int(started_before),)
            ).rowcount

        return ProcessedItemCount(max(deleted, 0))
