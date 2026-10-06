"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class IdempotencyClaimId(BasePrefixedTypedId):
    """
    Random identifier of one request's claim of an idempotency key: only the
    request holding it may store its answer or release the key, so a request
    whose claim was taken over (it outlived its lease) cannot overwrite the
    answer of the request that took over.
    """

    prefix = "idempotency_claim"


class IdempotencyRecordId(BasePrefixedTypedId):
    """
    Identifier of the record of one idempotency key.

    Derived (UUID v5) from the user who sent the key and the key itself, so
    keys of different users never meet and a retry finds its record by one
    read by id.
    """

    prefix = "idempotency_key"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
