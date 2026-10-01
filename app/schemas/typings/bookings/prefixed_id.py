"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class BookingId(BasePrefixedTypedId):
    """Random identifier of a booking."""

    prefix = "booking"


class LeadId(BasePrefixedTypedId):
    """Random identifier of a lead (request for a manager)."""

    prefix = "lead"


# Keep abc order for all non example types, if possible.
