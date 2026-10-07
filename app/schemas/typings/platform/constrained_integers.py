"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DatabaseConnectionCount(BaseConstrainedTypedInt):
    """How many Postgres connections of a process's pool are borrowed right now."""

    ge = 0


class DatabaseIdleSeconds(BaseConstrainedTypedInt):
    """
    How long a pooled Postgres connection may sit unused before the pool
    closes it (DB_POOL_MAX_IDLE_SECONDS), so a burst's connections go back
    to the server.
    """

    ge = 10
    le = 86_400


class DatabasePoolMinSize(BaseConstrainedTypedInt):
    """
    Idle Postgres connections one process keeps open however quiet it is
    (DB_POOL_MIN_SIZE), so the first requests after a pause need no connect.
    """

    ge = 0
    le = 512


class DatabasePoolSize(BaseConstrainedTypedInt):
    """
    How many Postgres connections one process may hold at once (DB_POOL_SIZE);
    by default as many as the API runs request threads.
    """

    ge = 1
    le = 512


class ElapsedMilliseconds(BaseConstrainedTypedInt):
    """Measured duration of an operation, in milliseconds."""

    ge = 0


class HeartbeatAgeSeconds(BaseConstrainedTypedInt):
    """How long ago the freshest background worker heartbeat was written."""

    ge = 0


class JobAttemptCount(BaseConstrainedTypedInt):
    """How many times a background job has been attempted."""

    ge = 0
    le = 1000


class JobClaimLimit(BaseConstrainedTypedInt):
    """How many due queued jobs a worker claims at once (its free slots)."""

    ge = 1
    le = 256


class JobIntervalSeconds(BaseConstrainedTypedInt):
    """How often a periodic background job runs, in seconds."""

    ge = 1
    le = 7 * 24 * 60 * 60


class JobLeaseSeconds(BaseConstrainedTypedInt):
    """
    How long a claimed job stays reserved for its worker without a
    heartbeat; after that another worker may take it over.
    """

    ge = 5
    le = 60 * 60


class JobRetentionDays(BaseConstrainedTypedInt):
    """How long finished queued jobs and periodic run records are kept, in days."""

    ge = 1
    le = 366


class KeysetReadLimit(BaseConstrainedTypedInt):
    """
    How many items a repository reads for one keyset page: the page size
    and one more, which tells whether another page follows.
    """

    ge = 1
    le = 1_000


class ListItemCount(BaseConstrainedTypedInt):
    """How many items of a cabinet list match a filter (all pages together)."""

    ge = 0


class LostJobLeaseCount(BaseConstrainedTypedInt):
    """
    How many attempts in a row of a queued job ended without a recorded
    result: its lease ran out because its worker process died (killed, out
    of memory) or lost the database while running it.
    """

    ge = 0
    le = 1000


class MigrationCount(BaseConstrainedTypedInt):
    """How many SQL migrations of this build a database has not applied yet."""

    ge = 0


class PageSize(BaseConstrainedTypedInt):
    """How many items one page of a cabinet list holds."""

    ge = 1
    le = 200


class PoolExhaustedSeconds(BaseConstrainedTypedInt):
    """How long every readiness probe has found the connection pool busy."""

    ge = 0


class ProcessedItemCount(BaseConstrainedTypedInt):
    """How many items one background job run processed."""

    ge = 0


class RateLimitRequestCount(BaseConstrainedTypedInt):
    """How many requests one rate-limit counter recorded in one window."""

    ge = 0


class RateWindowSeconds(BaseConstrainedTypedInt):
    """The length of a rate limit's counting window, in seconds."""

    ge = 1
    le = 24 * 60 * 60


class RequestsPerWindow(BaseConstrainedTypedInt):
    """How many requests one rate-limit counter allows in one window."""

    ge = 1
    le = 10_000_000


class RetryAfterSeconds(BaseConstrainedTypedInt):
    """How long a rate-limited caller should wait before asking again."""

    ge = 1
    le = 24 * 60 * 60


class ResidentMemoryBytes(BaseConstrainedTypedInt):
    """The memory a process holds in RAM (its resident set), in bytes."""

    ge = 0


class TestChatConcurrencyLimit(BaseConstrainedTypedInt):
    """
    Owner test-chat turns one API process answers at once
    (TEST_CHAT_MAX_CONCURRENCY): each holds a request thread for its model
    calls, so a few of them never take the threads the cabinet needs.
    """

    ge = 1
    le = 64


class ThreadPoolSize(BaseConstrainedTypedInt):
    """
    How many request handlers of the API run at the same time in worker
    threads (THREADPOOL_SIZE): the AnyIO thread limiter of the process.
    """

    ge = 1
    le = 512


class TurnSlotCount(BaseConstrainedTypedInt):
    """
    How many conversation turns of one kind one process runs at once; a
    turn beyond them waits for a place before it takes anything else.
    """

    ge = 1
    le = 512


class TurnSlotWaitSeconds(BaseConstrainedTypedInt):
    """How long a turn waits for a free place before it is refused."""

    ge = 1
    le = 3600


class WorkerLaneConcurrency(BaseConstrainedTypedInt):
    """How many jobs of one worker lane one worker process runs at the same time."""

    ge = 1
    le = 64


class WorkerLanePollSeconds(BaseConstrainedTypedInt):
    """
    How long an idle lane thread of the worker waits for a wake-up before
    it looks at the queue again (the safety net of a lost wake-up).
    """

    ge = 1
    le = 3600


class WorkerPollSeconds(BaseConstrainedTypedInt):
    """Pause between scheduler ticks of the background worker, in seconds."""

    ge = 1
    le = 3600


# Keep abc order for all non example types, if possible.
