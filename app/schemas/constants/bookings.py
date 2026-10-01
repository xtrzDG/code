from enum import StrEnum


class BookingStatus(StrEnum):
    """Lifecycle of a booking created by the assistant or the owner."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class LeadStatus(StrEnum):
    """Lifecycle of a lead (request for a manager)."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"
