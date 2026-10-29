"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class PeriodicJobRunId(BasePrefixedTypedId):
    """Random identifier of one recorded run of a periodic background job."""

    prefix = "periodic_run"


class QueuedJobId(BasePrefixedTypedId):
    """Random identifier of one queued background job."""

    prefix = "queued_job"


class WorkerInstanceId(BasePrefixedTypedId):
    """Random identifier of one running background worker process."""

    prefix = "worker"


# Keep abc order for all non example types, if possible.
