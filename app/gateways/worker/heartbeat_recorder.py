import logging
import socket
from collections.abc import Sequence

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.health import WorkerHeartbeatRepoContract
from app.contracts.storage import StorageScopeContract
from app.schemas.domain.jobs import PeriodicJobResult, WorkerHeartbeatDocument
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_strings import (
    ReleaseVersion,
    WorkerHostName,
)
from app.schemas.typings.platform.prefixed_id import WorkerInstanceId
from app.schemas.typings.storage.constrained_integers import DocumentCount

LOGGER: logging.Logger = logging.getLogger(__name__)
# Pulses of processes that stopped (restarts, deploys) are deleted after
# this long, when a worker starts.
HEARTBEAT_RETENTION_SECONDS: int = 24 * 60 * 60
UNKNOWN_HOST_NAME: WorkerHostName = WorkerHostName("unknown")


class WorkerHeartbeatRecorder:
    """
    Writes the pulse of this worker process (`worker_heartbeats`): which
    build it runs, since when, and how its periodic jobs ended last. The
    worker beats on every tick of its periodic thread, so GET /readyz can
    tell how long ago a worker was last alive. A pulse that cannot be
    written (the database is down) is logged and skipped: the worker goes
    on, and the next tick tries again.
    """

    def __init__(
        self,
        heartbeat_repo: WorkerHeartbeatRepoContract,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
        release: ReleaseVersion | None,
        host_name: WorkerHostName | None = None,
    ) -> None:
        self._heartbeat_repo: WorkerHeartbeatRepoContract = heartbeat_repo
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._release: ReleaseVersion | None = release
        self._host_name: WorkerHostName = (
            current_host_name() if host_name is None else host_name
        )
        self._worker_id: WorkerInstanceId = WorkerInstanceId()
        self._started_at: Microseconds = wall_clock.now_unix()

    @property
    def worker_id(self) -> WorkerInstanceId:
        return self._worker_id

    def start(self) -> None:
        """Delete the pulses of processes gone for a day, then beat once."""

        try:
            with self._storage_scope.platform_wide():
                deleted: DocumentCount = self._heartbeat_repo.delete_beaten_before(
                    self._wall_clock.now_unix_with_delta(
                        Seconds(-HEARTBEAT_RETENTION_SECONDS)
                    )
                )
        except ApplicationError as error:
            LOGGER.warning("Old worker heartbeats were not purged: %s", error)
        else:
            if int(deleted) > 0:
                LOGGER.info("Purged %d old worker heartbeats", int(deleted))

        self.beat([])

    def beat(self, periodic_results: Sequence[PeriodicJobResult]) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        heartbeat = WorkerHeartbeatDocument(
            id=self._worker_id,
            host_name=self._host_name,
            release=self._release,
            started_at=self._started_at,
            beat_at=now,
            periodic_results=list(periodic_results),
            created_at=self._started_at,
            updated_at=now,
        )
        try:
            with self._storage_scope.platform_wide():
                self._heartbeat_repo.save(heartbeat)
        except ApplicationError as error:
            LOGGER.warning("Worker heartbeat was not written: %s", error)


def current_host_name() -> WorkerHostName:
    """This machine's host name, or "unknown" when it is not a plain name."""

    try:
        return WorkerHostName(socket.gethostname())
    except ValueError:
        return UNKNOWN_HOST_NAME
