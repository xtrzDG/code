"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ElapsedMilliseconds(BaseConstrainedTypedInt):
    """Measured duration of an operation, in milliseconds."""

    ge = 0


class JobAttemptCount(BaseConstrainedTypedInt):
    """How many times a background job has been attempted."""

    ge = 0
    le = 1000


class JobIntervalSeconds(BaseConstrainedTypedInt):
    """How often a periodic background job runs, in seconds."""

    ge = 1
    le = 7 * 24 * 60 * 60


class PageSize(BaseConstrainedTypedInt):
    """How many items one page of a cabinet list holds."""

    ge = 1
    le = 200


class ProcessedItemCount(BaseConstrainedTypedInt):
    """How many items one background job run processed."""

    ge = 0


class WorkerPollSeconds(BaseConstrainedTypedInt):
    """Pause between scheduler ticks of the background worker, in seconds."""

    ge = 1
    le = 3600


# Keep abc order for all non example types, if possible.
