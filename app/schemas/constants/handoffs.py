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


class HandoffStatus(StrEnum):
    """Delivery state of a handoff to the business staff."""

    PENDING = "pending"
    NOTIFIED = "notified"
    NOTIFICATION_FAILED = "notification_failed"
    RESOLVED = "resolved"


class ManagerContactChannel(StrEnum):
    """Where staff receive handoffs and new leads."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
