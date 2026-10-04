from enum import StrEnum


class ResourceKind(StrEnum):
    """What is booked, as in the concept's resources table."""

    TABLE = "table"
    ROOM = "room"
    STAFF = "staff"
    ARENA = "arena"
    BAY = "bay"
    VEHICLE = "vehicle"
    SLOT = "slot"


class BookingUnit(StrEnum):
    """How a resource is booked: for a time slot or for nights (hotels)."""

    TIME_SLOT = "time_slot"
    NIGHT = "night"


class BookingStatus(StrEnum):
    """Lifecycle of a booking."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class LeadType(StrEnum):
    """Kind of request passed to a manager."""

    BANQUET = "banquet"
    GROUP = "group"
    CORPORATE = "corporate"
    ORDER = "order"
    VIEWING = "viewing"
    OTHER = "other"


class LeadStatus(StrEnum):
    """Lifecycle of a lead."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"


class BookingReminderKind(StrEnum):
    """
    Which reminder of a booking a message is: the one the day before
    (DAY_BEFORE). A booking gets each kind once per start time, so a moved
    booking is reminded of its new time.
    """

    DAY_BEFORE = "day_before"


class BookingOrder(StrEnum):
    """
    Order of the cabinet's booking list by start time: upcoming bookings
    read earliest first, past ones latest first.
    """

    EARLIEST_FIRST = "earliest_first"
    LATEST_FIRST = "latest_first"


class BookingRefusalCode(StrEnum):
    """
    Why a booking could not be placed, as the `reasons[].code` of the error,
    so the cabinet shows the reason in the user's language.
    """

    CLOSED = "closed"
    TOO_SOON = "too_soon"
    TIME_REQUIRED = "time_required"
    TAKEN = "taken"
    PARTY_TOO_LARGE = "party_too_large"
    NO_SEATING_RESOURCE = "no_seating_resource"
    # A service, package or room type no name or id matches, or several.
    UNKNOWN_SERVICE = "unknown_service"
    AMBIGUOUS_SERVICE = "ambiguous_service"
    # A master, room or table no name or id matches, or several.
    UNKNOWN_RESOURCE = "unknown_resource"
    AMBIGUOUS_RESOURCE = "ambiguous_resource"
    # The chosen resource does not perform the chosen service.
    NOT_PERFORMED = "not_performed"
