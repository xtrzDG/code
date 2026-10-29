"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class BookingId(BasePrefixedTypedId):
    """Random identifier of a booking."""

    prefix = "booking"


class CalendarAuthorizationStateId(BasePrefixedTypedId):
    """Random identifier of one pending calendar OAuth authorization."""

    prefix = "calendar_authorization_state"


class CalendarConnectionId(BasePrefixedTypedId):
    """Random identifier of a business calendar connection."""

    prefix = "calendar_connection"


class CalendarEventLinkId(BasePrefixedTypedId):
    """Random identifier of the link between a booking and a calendar event."""

    prefix = "calendar_event_link"


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
