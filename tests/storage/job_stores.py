"""The job queue and periodic run stores on either storage, for parity tests."""

import pytest

from app.adapters.storage.postgres.postgres_periodic_job_run_store_adapter import (
    PostgresPeriodicJobRunStoreAdapter,
)
from app.adapters.storage.postgres.postgres_queued_job_claim_adapter import (
    PostgresQueuedJobClaimAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.job_repositories import (
    PeriodicJobRunRepository,
    QueuedJobRepository,
)
from app.schemas.domain.jobs import PeriodicJobRunDocument, QueuedJobDocument
from app.utilities.jobs.job_wakeup_signal import JobWakeupSignal
from tests.platform.worker_fakes import JobStores, build_job_stores
from tests.storage.conftest import PostgresCollectionFactory


def build_postgres_job_stores(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
) -> JobStores:
    jobs = postgres_collections(QueuedJobDocument, "queued_jobs")
    runs = postgres_collections(PeriodicJobRunDocument, "periodic_job_runs")
    return JobStores(
        job_repo=QueuedJobRepository(
            jobs, PostgresQueuedJobClaimAdapter(connection_pool)
        ),
        periodic_run_repo=PeriodicJobRunRepository(
            PostgresPeriodicJobRunStoreAdapter(runs, connection_pool)
        ),
        job_wakeup=JobWakeupSignal(),
    )


def job_stores_for(request: pytest.FixtureRequest) -> JobStores:
    """In-memory or Postgres stores, by the fixture's parameter."""

    if request.param == "in_memory":
        return build_job_stores()

    connection_pool: PostgresConnectionPoolClient = request.getfixturevalue(
        "connection_pool"
    )
    postgres_collections: PostgresCollectionFactory = request.getfixturevalue(
        "postgres_collections"
    )
    return build_postgres_job_stores(connection_pool, postgres_collections)
