import secrets
import threading
from dataclasses import dataclass

from app.schemas.dto.job_queue import HeldJobLease
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId

LEASE_TOKEN_BYTES: int = 16


def new_lease_token() -> JobLeaseToken:
    """A random token for one claim (32 hex digits)."""

    return JobLeaseToken(secrets.token_hex(LEASE_TOKEN_BYTES))


@dataclass(frozen=True)
class HeldPeriodicRun:
    """A periodic job this process runs right now, with its claim's token."""

    job_name: JobName
    period_key: JobPeriodKey
    lease_token: JobLeaseToken


class HeldLeases:
    """
    The leases this worker process holds right now: queued jobs running on
    lane threads and the periodic job running on the periodic thread. The
    heartbeat extends all of them; the threads add and remove their own.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._jobs: dict[QueuedJobId, JobLeaseToken] = {}
        self._periodic_runs: dict[JobName, HeldPeriodicRun] = {}

    def hold_job(self, job_id: QueuedJobId, lease_token: JobLeaseToken) -> None:
        with self._lock:
            self._jobs[job_id] = lease_token

    def release_job(self, job_id: QueuedJobId) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def holds_job(self, job_id: QueuedJobId, lease_token: JobLeaseToken) -> bool:
        """Whether the job still runs here under this claim's token."""

        with self._lock:
            return self._jobs.get(job_id) == lease_token

    def hold_periodic_run(self, run: HeldPeriodicRun) -> None:
        with self._lock:
            self._periodic_runs[run.job_name] = run

    def release_periodic_run(self, job_name: JobName) -> None:
        with self._lock:
            self._periodic_runs.pop(job_name, None)

    def jobs(self) -> list[HeldJobLease]:
        with self._lock:
            return [
                HeldJobLease(job_id=job_id, lease_token=lease_token)
                for job_id, lease_token in self._jobs.items()
            ]

    def periodic_runs(self) -> list[HeldPeriodicRun]:
        with self._lock:
            return list(self._periodic_runs.values())
