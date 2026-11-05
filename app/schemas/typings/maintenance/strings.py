"""Keep abc order."""

from base_typed_string import BaseTypedString


class NoBackfillReason(BaseTypedString):
    """
    Why a lookup column added to an existing table needs no backfill, in
    one English sentence (the rows written before it cannot hold the field).
    """


# Keep abc order for all non example types, if possible.
