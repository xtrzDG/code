from enum import StrEnum


class StaffAlertEvent(StrEnum):
    """
    What staff can be told about: a conversation passed to a person, a new
    request, a booking (new, moved or cancelled). Each staff contact and
    each cabinet user chooses which of them reach them.
    """

    HANDOFF = "handoff"
    LEAD = "lead"
    BOOKING = "booking"


class StaffLinkTarget(StrEnum):
    """The cabinet page a notification link opens (after sign-in)."""

    CONVERSATION = "conversation"
    LEAD = "lead"
    BOOKING = "booking"
    NOTIFICATIONS = "notifications"


class StaffTextStyle(StrEnum):
    """
    How much a staff notification says. DETAILED (Telegram and WhatsApp,
    chats the staff member linked): the summary, the customer's name and
    phone. BRIEF (e-mail, SMS, a device notification, all readable on a
    locked screen): what happened and the link, nothing about the customer.
    """

    DETAILED = "detailed"
    BRIEF = "brief"


class WebPushUrgency(StrEnum):
    """How soon a push service should wake the device (RFC 8030 Urgency)."""

    NORMAL = "normal"
    HIGH = "high"


class StaffBookingChange(StrEnum):
    """What happened to a booking staff are told about."""

    CREATED = "created"
    MOVED = "moved"
    CANCELLED = "cancelled"
