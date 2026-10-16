"""Wake-ups of the job queue between processes through Postgres NOTIFY / LISTEN."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import LiteralString

import psycopg
from typed_time_provider import Microseconds

from app.clients.postgres import postgres_notification_listener
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_notification_listener import (
    ListenerConnection,
    ListenerConnector,
    PostgresNotificationListener,
)
from app.contracts.jobs import JobWakeupContract
from app.schemas.constants.jobs import JobLane
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.jobs.job_wakeup_payloads import (
    decode_job_wakeup,
    encode_job_wakeup,
)
from app.utilities.jobs.job_wakeup_signal import JobWakeupSignal

LOGGER: logging.Logger = logging.getLogger(__name__)

JOB_WAKEUP_CHANNEL: LiteralString = "workshop_jobs"
NOTIFY_STATEMENT: LiteralString = "select pg_notify(%s, %s)"
WAKEUP_APPLICATION_NAME: str = "assistant-workshop-job-wakeup"
WAKEUP_LISTENER_THREAD_NAME: str = "job-wakeup-listener"
# On stop the listener thread is given this long to close its session.
LISTENER_STOP_SECONDS: float = 2.0


def connect_wakeup_listener(database_url: DatabaseUrl) -> ListenerConnection:
    """The worker's LISTEN session for job wake-ups (named in pg_stat_activity)."""

    return postgres_notification_listener.connect_listener(
        database_url, WAKEUP_APPLICATION_NAME
    )


class PostgresJobWakeupAdapter(JobWakeupContract):
    """
    A webhook's message is queued by an API instance and answered by a
    separate worker process; this carries "a job is due in lane X" from one
    to the other in milliseconds instead of a poll interval.

    - `notify` is `select pg_notify('workshop_jobs', <lane>)` on the pool's
      connection of the calling thread. The job queue calls it inside the
      enqueue's transaction, so Postgres sends it when the job row commits
      (never before, and not at all when the transaction rolls back): a
      woken worker always finds the job. It also works through a
      transaction pooler. A job queued for later sends
      `<lane>@<run_at>` (`notify_at`), and every listening worker arms a
      timer for that moment (`JobWakeupSignal.notify_at`): a burst of a
      customer's messages is answered the moment the customer has been
      quiet long enough, not at the next poll.
    - `listen` holds one LISTEN session for the block (the worker, while
      its lane threads run; `PostgresNotificationListener` reconnects with
      growing pauses) and sets the lane's in-process event for every
      notification; after each (re)connect every lane is woken, because
      notifications sent meanwhile are lost.
    - `wait` waits on that in-process event; the lane threads' poll stays
      the safety net when a notification is lost.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        connect: ListenerConnector,
        signal: JobWakeupSignal | None = None,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._connect: ListenerConnector = connect
        self._signal: JobWakeupSignal = JobWakeupSignal() if signal is None else signal

    def notify(self, lane: JobLane) -> None:
        self._send(lane, None)

    def notify_at(self, lane: JobLane, run_at: Microseconds) -> None:
        self._send(lane, run_at)

    def _send(self, lane: JobLane, run_at: Microseconds | None) -> None:
        try:
            with self._connection_pool.connection() as connection:
                connection.execute(
                    NOTIFY_STATEMENT,
                    (JOB_WAKEUP_CHANNEL, encode_job_wakeup(lane, run_at)),
                )
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Could not signal the {lane.value} job lane ({type(error).__name__})."
            ) from error

    def wait(self, lane: JobLane, timeout_seconds: float) -> bool:
        return self._signal.wait(lane, timeout_seconds)

    @contextmanager
    def listen(self) -> Generator[None]:
        listener = PostgresNotificationListener(
            connect=self._connect,
            channel=JOB_WAKEUP_CHANNEL,
            on_notification=self._receive,
            on_listening=self._signal.notify_all,
            thread_name=WAKEUP_LISTENER_THREAD_NAME,
        )
        with self._signal.listen():
            listener.ensure_started()
            try:
                yield
            finally:
                listener.stop(timeout_seconds=LISTENER_STOP_SECONDS)

    def _receive(self, payload: str) -> None:
        wakeup: tuple[JobLane, Microseconds | None] | None = decode_job_wakeup(payload)
        if wakeup is None:
            # A lane of a newer release during a deploy: its own workers
            # take those jobs.
            LOGGER.debug("Ignored a wake-up for an unknown job lane")
            return

        lane, run_at = wakeup
        if run_at is None:
            self._signal.notify(lane)
        else:
            self._signal.notify_at(lane, run_at)
