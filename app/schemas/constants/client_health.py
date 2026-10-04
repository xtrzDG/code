from enum import StrEnum


class ClientHealthStatus(StrEnum):
    """Overall state of a client business in the platform admin view."""

    HEALTHY = "healthy"
    ATTENTION = "attention"
    CRITICAL = "critical"


class ClientHealthIssue(StrEnum):
    """
    One reason a client needs attention.

    Critical: the assistant is limited (leads only) or loses money; the rest
    asks for a look.
    """

    NO_SUBSCRIPTION = "no_subscription"
    FIRST_PAYMENT_PENDING = "first_payment_pending"
    PAYMENT_PAST_DUE = "payment_past_due"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    LEADS_ONLY_MODE = "leads_only_mode"
    NOT_PUBLISHED = "not_published"
    AUTOTESTS_FAILED = "autotests_failed"
    TOOL_ERRORS = "tool_errors"
    MANY_HANDOFFS = "many_handoffs"
    OPEN_QUESTIONS = "open_questions"
    PACKAGE_EXCEEDED = "package_exceeded"
    NEGATIVE_MARGIN = "negative_margin"
    SLOW_REPLIES = "slow_replies"
    GUARD_SPIKE = "guard_spike"


class AdminClientSort(StrEnum):
    """
    Order of the platform admin's client list.

    HEALTH: critical first, then more issues first. NAME: A to Z. USAGE: the
    fullest package first. MARGIN: the lowest margin first. COST: the
    largest provider cost first. REVENUE: the largest revenue first, per
    currency. Unknown values go last; ties keep health, then name order.
    """

    HEALTH = "health"
    NAME = "name"
    USAGE = "usage"
    MARGIN = "margin"
    COST = "cost"
    REVENUE = "revenue"


class CabinetSection(StrEnum):
    """Cabinet page of a business (concept section 8)."""

    DASHBOARD = "dashboard"
    CONVERSATIONS = "conversations"
    BOOKINGS = "bookings"
    LEADS = "leads"
    HANDOFFS = "handoffs"
    KNOWLEDGE = "knowledge"
    ASSISTANT = "assistant"
    CHANNELS = "channels"
    BILLING = "billing"
    SETTINGS = "settings"
