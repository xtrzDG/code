from enum import StrEnum


class HandoffReason(StrEnum):
    """Why the assistant passed a conversation to a human."""

    CUSTOMER_REQUEST = "customer_request"
    COMPLAINT = "complaint"
    VIP_GUEST = "vip_guest"
    NON_STANDARD_REQUEST = "non_standard_request"
    UNKNOWN_ANSWER = "unknown_answer"
    EMERGENCY = "emergency"
    SENSITIVE_TOPIC = "sensitive_topic"
    PROFILE_RULE = "profile_rule"
    UNVERIFIED_NUMBERS = "unverified_numbers"


class HandoffUrgency(StrEnum):
    """How fast staff should react."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class HandoffStatus(StrEnum):
    """Delivery and resolution state of a handoff."""

    PENDING = "pending"
    NOTIFIED = "notified"
    NOTIFICATION_FAILED = "notification_failed"
    RESOLVED = "resolved"


class ManagerContactChannel(StrEnum):
    """Where staff receive handoffs, bookings and leads."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
