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


class ClientTimelineKind(StrEnum):
    """
    What a line of a client's story on the admin client page is about:
    the platform team's ADMIN_ACTIONs on the account, SUPPORT looks into
    the cabinet, CHANGES the client's team made (from the audit log),
    BILLING (invoices, payments, credit, subscription steps), HEALTH
    changes, the setup's MILESTONES and the ONBOARDING request.
    """

    ADMIN_ACTION = "admin_action"
    SUPPORT = "support"
    CHANGE = "change"
    BILLING = "billing"
    HEALTH = "health"
    MILESTONE = "milestone"
    ONBOARDING = "onboarding"


class ClientTimelineEvent(StrEnum):
    """
    One line of a client's story, a code the admin pages word in their
    language. AUDIT_ENTRY is any other audit log entry (its action and
    entity say what); the rest name the step itself.
    """

    AUDIT_ENTRY = "audit_entry"
    INVOICE_ISSUED = "invoice_issued"
    INVOICE_PAID = "invoice_paid"
    INVOICE_FAILED = "invoice_failed"
    CREDIT_USED = "credit_used"
    TRIAL_STARTED = "trial_started"
    SUBSCRIBED = "subscribed"
    PLAN_CHANGED = "plan_changed"
    CANCELLED = "cancelled"
    PAYMENT_FAILED = "payment_failed"
    HEALTH_CHANGED = "health_changed"
    BUSINESS_CREATED = "business_created"
    LAUNCH_SUCCEEDED = "launch_succeeded"
    LAUNCH_BLOCKED = "launch_blocked"
    DPA_ACCEPTED = "dpa_accepted"
    CHANNEL_CONNECTED = "channel_connected"
    TEST_CHAT_TRIED = "test_chat_tried"
    WENT_LIVE = "went_live"
    FIRST_REAL_CONVERSATION = "first_real_conversation"
    FIRST_BOOKING = "first_booking"
    FIRST_HANDOFF = "first_handoff"
    ONBOARDING_REQUESTED = "onboarding_requested"


class AdminDigestKind(StrEnum):
    """
    A digest the platform team gets through the platform bot: once a day,
    the CRITICAL_CLIENTS that newly turned critical since the last one.
    """

    CRITICAL_CLIENTS = "critical_clients"
