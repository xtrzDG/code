"""Several workers on one Postgres queue: every job runs exactly once."""

import threading
import time
from collections import Counter

from typed_time_provider import Microseconds

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.dto.job_queue import JobClaimRequest, PeriodicRunStart
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import JobClaimLimit
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
    JobSerialKey,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.jobs.periodic_runs import decide_periodic_run_start
from tests.platform.lane_fakes import running_worker, wait_until
from tests.platform.worker_fakes import RUN_AUTOTESTS, ControlledClock, build_worker
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.job_stores import build_postgres_job_stores


class RecordingOperator:
    """Records every run and whether two jobs of one serial key overlapped."""

    def __init__(self) -> None:
        self.runs: Counter[QueuedJobId] = Counter()
        self.overlaps: int = 0
        self._running_keys: set[str] = set()
        self._lock: threading.Lock = threading.Lock()

    def operate(self, input_data: QueuedJobInput) -> JobReport:
        key: str = str(input_data.payload)
        with self._lock:
            self.runs[input_data.job_id] += 1
            if key != "{}" and key in self._running_keys:
                self.overlaps += 1
            self._running_keys.add(key)

        time.sleep(0.005)
        with self._lock:
            self._running_keys.discard(key)

        return JobReport()


def test_two_workers_on_one_queue_run_each_job_once(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
) -> None:
    clock = ControlledClock()
    stores = build_postgres_job_stores(connection_pool, postgres_collections)
    operator = RecordingOperator()
    workers = [
        build_worker(
            clock, [], {RUN_AUTOTESTS: operator}, stores=stores, poll_seconds=1
        )
        for _ in range(2)
    ]
    queue = workers[0].queue
    job_ids: list[QueuedJobId] = [
        queue.enqueue(RUN_AUTOTESTS, JobPayloadJson("{}"), None) for _ in range(30)
    ]
    for index in range(12):
        business_key = f"autotests:business_{index % 3}"
        job_ids.append(
            queue.enqueue(
                RUN_AUTOTESTS,
                JobPayloadJson(f'"{business_key}"'),
                None,
                lane=JobLane.AUTOTESTS,
                serial_key=JobSerialKey(business_key),
            )
        )

    with running_worker(workers[0].worker), running_worker(workers[1].worker):
        assert wait_until(lambda: len(operator.runs) == len(job_ids), timeout=30.0)

    assert set(operator.runs) == set(job_ids)
    assert set(operator.runs.values()) == {1}
    assert operator.overlaps == 0
    for job_id in job_ids:
        job = stores.job_repo.get(job_id)
        assert job is not None and job.status is QueuedJobStatus.DONE


def test_concurrent_claims_never_share_a_job(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
) -> None:
    clock = ControlledClock()
    stores = build_postgres_job_stores(connection_pool, postgres_collections)
    queue = build_worker(clock, [], stores=stores).queue
    job_ids = {
        queue.enqueue(JobName("send_outbound"), JobPayloadJson("{}"), None)
        for _ in range(60)
    }
    now: Microseconds = clock.wall_clock().now_unix()
    claimed: list[QueuedJobId] = []
    lock = threading.Lock()

    def claim_until_empty(token: str) -> None:
        while True:
            jobs = stores.job_repo.claim_due(
                JobClaimRequest(
                    lane=JobLane.DEFAULT,
                    now=now,
                    limit=JobClaimLimit(3),
                    lease_until=Microseconds(int(now) + 60_000_000),
                    lease_token=JobLeaseToken(token * 32),
                )
            )
            if not jobs:
                return

            with lock:
                claimed.extend(job.id for job in jobs)

    threads = [
        threading.Thread(target=claim_until_empty, args=(digit,)) for digit in "1234"
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30.0)

    assert sorted(claimed) == sorted(job_ids)


def test_a_periodic_run_is_left_alone_while_another_worker_decides(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
) -> None:
    stores = build_postgres_job_stores(connection_pool, postgres_collections)
    digest = JobName("send_daily_digest")
    today = JobPeriodKey("2026-09-21")
    now = Microseconds(1_790_000_000_000_000)
    decide = decide_periodic_run_start(
        PeriodicRunStart(
            job_name=digest,
            period_key=today,
            now=now,
            lease_until=Microseconds(int(now) + 60_000_000),
            lease_token=JobLeaseToken("e" * 32),
        )
    )

    with connection_pool.transaction() as other_worker:
        other_worker.execute(
            "select pg_advisory_xact_lock("
            "hashtextextended('periodic_job_runs:' || %s::text, 0))",
            (str(digest),),
        )
        while_locked = stores.periodic_run_repo.claim(digest, today, decide)

    after_unlock = stores.periodic_run_repo.claim(digest, today, decide)

    assert while_locked is None
    assert after_unlock is not None
    assert stores.periodic_run_repo.get(digest, today) == after_unlock
