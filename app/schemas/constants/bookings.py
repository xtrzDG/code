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


class BookingOrder(StrEnum):
    """
    Order of the cabinet's booking list by start time: upcoming bookings
    read earliest first, past ones latest first.
    """

    EARLIEST_FIRST = "earliest_first"
    LATEST_FIRST = "latest_first"
