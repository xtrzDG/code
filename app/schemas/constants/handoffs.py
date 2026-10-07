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


class HandoffSummaryCode(StrEnum):
    """
    What happened, for a handoff the platform itself created (the model
    writes its own summary for the ones it creates). Staff read it in
    their own language: the cabinet and every notification render the
    code, with the quoted text and the flagged values, from their own
    dictionaries.
    """

    MODEL_DECLINED = "model_declined"
    MODEL_UNAVAILABLE = "model_unavailable"
    ANSWER_UNFINISHED = "answer_unfinished"
    UNVERIFIED_VALUES = "unverified_values"
    CALL_BOOKING_UNVERIFIED_VALUES = "call_booking_unverified_values"
    CALL_REQUEST_UNVERIFIED_VALUES = "call_request_unverified_values"
    REPLY_UNDELIVERED = "reply_undelivered"
    DATA_ERASED = "data_erased"


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
