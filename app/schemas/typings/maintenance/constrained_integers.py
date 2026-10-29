"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DataTaskBatchCount(BaseConstrainedTypedInt):
    """How many keyset batches a post-deploy data task has run so far."""

    ge = 0


class DataTaskBatchSize(BaseConstrainedTypedInt):
    """
    How many rows one batch of a post-deploy data task looks at, each batch
    its own short transaction (DATA_TASKS_BATCH_SIZE, 5,000 by default):
    small enough that its row locks last milliseconds, large enough that a
    big table takes few round trips.
    """

    ge = 100
    le = 50_000


class DataTaskCount(BaseConstrainedTypedInt):
    """How many post-deploy data tasks are in one state (pending, failed)."""

    ge = 0


class DataTaskFailureCount(BaseConstrainedTypedInt):
    """
    How many batches of a data task failed in a row (a database error, a
    row that stayed locked); back to 0 after a batch that worked.
    """

    ge = 0


class DataTaskRunSeconds(BaseConstrainedTypedInt):
    """
    How long one run of the data-task job may keep starting batches before
    it hands the rest to its next run: shorter than the job's period, so
    two runs never overlap.
    """

    ge = 1
    le = 3_600


# Keep abc order for all non example types, if possible.
