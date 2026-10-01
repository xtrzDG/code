"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class BookingId(BasePrefixedTypedId):
    """Random identifier of a booking."""

    prefix = "booking"


class LeadId(BasePrefixedTypedId):
    """Random identifier of a lead (request for a manager)."""

    prefix = "lead"


class ResourceId(BasePrefixedTypedId):
    """Random identifier of a bookable resource."""

    prefix = "resource"


class ScheduleExceptionId(BasePrefixedTypedId):
    """Random identifier of a holiday or special-hours day."""

    prefix = "schedule_exception"


# Keep abc order for all non example types, if possible.
