"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ElapsedMilliseconds(BaseConstrainedTypedInt):
    """Measured duration of an operation, in milliseconds."""

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


class ListItemCount(BaseConstrainedTypedInt):
    """How many items of a cabinet list match a filter (all pages together)."""

    ge = 0


class PageSize(BaseConstrainedTypedInt):
    """How many items one page of a cabinet list holds."""

    ge = 1
    le = 200


class ProcessedItemCount(BaseConstrainedTypedInt):
    """How many items one background job run processed."""

    ge = 0


class RetryAfterSeconds(BaseConstrainedTypedInt):
    """How long a rate-limited caller should wait before asking again."""

    ge = 1
    le = 24 * 60 * 60


class WorkerLaneConcurrency(BaseConstrainedTypedInt):
    """How many jobs of one worker lane one worker process runs at the same time."""

    ge = 1
    le = 64


class WorkerPollSeconds(BaseConstrainedTypedInt):
    """Pause between scheduler ticks of the background worker, in seconds."""

    ge = 1
    le = 3600


# Keep abc order for all non example types, if possible.
