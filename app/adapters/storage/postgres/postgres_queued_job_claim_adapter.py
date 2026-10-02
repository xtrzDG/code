from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.job_claim_queries import (
    CLAIM_DUE,
    EXTEND_LEASES,
    FINISHED_JOB_STATUSES,
    LANE_CLAIM_LOCK,
    PURGE_BATCH_SIZE,
    PURGE_FINISHED_BATCH,
    QUEUED_JOBS_COLLECTION,
    RELEASE_EXPIRED_LEASES,
    build_list_page_query,
)
from app.adapters.storage.postgres.platform_transaction import (
    platform_transaction,
    read_document_text,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.jobs import QueuedJobClaimAdapterContract
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import (
    ExpiredLeaseRelease,
    JobClaimRequest,
    JobLeaseExtension,
    QueuedJobPageQuery,
)
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.prefixed_id import QueuedJobId


class PostgresQueuedJobClaimAdapter(QueuedJobClaimAdapterContract):
    """
    The leased job queue on `workshop.queued_jobs` (EU Postgres), safe for
    any number of worker processes and threads:

    - a claim is one `update … from (select … for update skip locked limit
      N) returning`, so two workers never get the same job and never wait
      for each other's rows; claims of one lane take a transaction-level
      advisory lock first, so a serial key never runs twice at once;
    - a heartbeat moves only leases still held under their token;
    - the reaper releases jobs whose lease ended in one statement.
    """

    def __init__(self, connection_pool: PostgresConnectionPoolClient) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool

    def claim_due(self, claim: JobClaimRequest) -> list[QueuedJobDocument]:
        with platform_transaction(
            self._connection_pool, QUEUED_JOBS_COLLECTION
        ) as connection:
            connection.execute(LANE_CLAIM_LOCK, (claim.lane.value,))
            rows: list[TupleRow] = connection.execute(
                CLAIM_DUE,
                {
                    "lane": claim.lane.value,
                    "now": int(claim.now),
                    "limit": int(claim.limit),
                    "lease_until": int(claim.lease_until),
                    "lease_token": str(claim.lease_token),
                },
            ).fetchall()

        claimed: list[QueuedJobDocument] = self._parse(rows)
        return sorted(claimed, key=lambda job: job.run_at)

    def extend_leases(self, extension: JobLeaseExtension) -> list[QueuedJobId]:
        if not extension.leases:
            return []

        with platform_transaction(
            self._connection_pool, QUEUED_JOBS_COLLECTION
        ) as connection:
            rows: list[TupleRow] = connection.execute(
                EXTEND_LEASES,
                {
                    "lease_until": int(extension.lease_until),
                    "job_ids": [str(lease.job_id) for lease in extension.leases],
                    "lease_tokens": [
                        str(lease.lease_token) for lease in extension.leases
                    ],
                },
            ).fetchall()

        extended_keys: set[str] = {str(row[0]) for row in rows}
        return [
            lease.job_id
            for lease in extension.leases
            if str(lease.job_id) in extended_keys
        ]

    def release_expired_leases(
        self,
        release: ExpiredLeaseRelease,
    ) -> list[QueuedJobDocument]:
        with platform_transaction(
            self._connection_pool, QUEUED_JOBS_COLLECTION
        ) as connection:
            rows: list[TupleRow] = connection.execute(
                RELEASE_EXPIRED_LEASES,
                {
                    "now": int(release.now),
                    "max_attempts": int(release.max_attempts),
                    "error_text": str(release.error_text),
                },
            ).fetchall()

        return self._parse(rows)

    def list_page(self, query: QueuedJobPageQuery) -> list[QueuedJobDocument]:
        statement = build_list_page_query(
            has_status=query.status is not None,
            has_name=query.name is not None,
            has_position=query.after is not None,
        )
        parameters: dict[str, object] = {"limit": int(query.page_size) + 1}
        if query.status is not None:
            parameters["status"] = query.status.value

        if query.name is not None:
            parameters["name"] = str(query.name)

        if query.after is not None:
            parameters["after_updated_at"] = int(query.after.updated_at)
            parameters["after_key"] = str(query.after.job_id)

        with platform_transaction(
            self._connection_pool, QUEUED_JOBS_COLLECTION
        ) as connection:
            rows: list[TupleRow] = connection.execute(statement, parameters).fetchall()

        return self._parse(rows)

    def purge_finished(self, finished_before: Microseconds) -> ProcessedItemCount:
        purged: int = 0
        while True:
            with platform_transaction(
                self._connection_pool, QUEUED_JOBS_COLLECTION
            ) as connection:
                deleted: int = connection.execute(
                    PURGE_FINISHED_BATCH,
                    {
                        "statuses": list(FINISHED_JOB_STATUSES),
                        "finished_before": int(finished_before),
                        "batch_size": PURGE_BATCH_SIZE,
                    },
                ).rowcount

            purged += max(deleted, 0)
            if deleted < PURGE_BATCH_SIZE:
                return ProcessedItemCount(purged)

    def _parse(self, rows: list[TupleRow]) -> list[QueuedJobDocument]:
        return [
            QueuedJobDocument.model_validate_json(
                read_document_text(row, QUEUED_JOBS_COLLECTION)
            )
            for row in rows
        ]
