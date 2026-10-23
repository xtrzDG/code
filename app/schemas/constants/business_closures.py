from enum import StrEnum


class BusinessClosureReason(StrEnum):
    """
    Why a business is closing: an owner closed it (OWNER_REQUEST), or its
    subscription ended unpaid OFFBOARD_AFTER_DAYS ago (UNPAID_SUBSCRIPTION:
    paying again keeps it).
    """

    OWNER_REQUEST = "owner_request"
    UNPAID_SUBSCRIPTION = "unpaid_subscription"


class BusinessClosureState(StrEnum):
    """
    Where a business stands on its way out: ACTIVE (no closure),
    PENDING_DELETION (closed: the assistant is paused, the channels are off
    and the data is deleted at `delete_after` unless the closure is
    cancelled) or DELETING (the deletion has begun and cannot be stopped).
    """

    ACTIVE = "active"
    PENDING_DELETION = "pending_deletion"
    DELETING = "deleting"


class BusinessDeletionState(StrEnum):
    """A ledger entry: the deletion runs (IN_PROGRESS) or is done (COMPLETED)."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class DeprovisionTarget(StrEnum):
    """
    What a business's deletion switches off outside the platform: its voice
    agent, its Telegram bots' webhooks, its Meta pages' and WhatsApp
    accounts' subscriptions, its Google Calendar access, its rented numbers
    and its automatic payments.
    """

    VOICE_AGENT = "voice_agent"
    TELEGRAM_WEBHOOK = "telegram_webhook"
    META_SUBSCRIPTION = "meta_subscription"
    GOOGLE_CALENDAR = "google_calendar"
    PHONE_NUMBER = "phone_number"
    PAYMENT_SCHEDULE = "payment_schedule"


class DeprovisionOutcome(StrEnum):
    """
    How one deprovisioning went: DONE, NOTHING (the business had none) or
    SKIPPED (the provider could not be reached and the credential that
    reaches it is deleted with the business: nothing of ours can use it).
    """

    DONE = "done"
    NOTHING = "nothing"
    SKIPPED = "skipped"


class ClosureNoticeKind(StrEnum):
    """
    What the owners are told: an owner closed the business, it closed for
    non-payment, or the closure was cancelled.
    """

    OPENED_BY_OWNER = "opened_by_owner"
    OPENED_UNPAID = "opened_unpaid"
    CANCELLED = "cancelled"
