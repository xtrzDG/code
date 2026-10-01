"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class QueuedJobId(BasePrefixedTypedId):
    """Random identifier of one queued background job."""

    prefix = "queued_job"


# Keep abc order for all non example types, if possible.
