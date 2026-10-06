from enum import StrEnum


class CancellationReason(StrEnum):
    """
    Why an owner cancels, chosen in the cancel dialog (with optional words
    of their own). The founder reads them on the admin Metrics page; the
    dialog answers some with an offer (`RetentionOfferKind`).
    """

    TOO_EXPENSIVE = "too_expensive"
    SEASONAL_BREAK = "seasonal_break"
    NOT_ENOUGH_USE = "not_enough_use"
    MISSING_FEATURE = "missing_feature"
    ANSWER_QUALITY = "answer_quality"
    SWITCHED_PROVIDER = "switched_provider"
    CLOSING_BUSINESS = "closing_business"
    OTHER = "other"


class RetentionOfferKind(StrEnum):
    """
    What the cancel dialog offers instead of cancelling: a seasonal PAUSE
    (the assistant takes requests for a fraction of the price), a
    DOWNGRADE to the next cheaper plan, or a one-time CREDIT on the
    business's ledger.
    """

    PAUSE = "pause"
    DOWNGRADE = "downgrade"
    CREDIT = "credit"


class SubscriptionEventKind(StrEnum):
    """
    One step of a subscription's life (`subscription_events`): CANCELLED
    (with the reason), OFFER_ACCEPTED, PAUSE_SCHEDULED (by the owner),
    PAUSE_STARTED (by the pause job at the end of the paid period),
    RESUMED (by the owner, or by the job when the pause ran out; before
    its start it calls the pause off), WIN_BACK_SENT.
    """

    CANCELLED = "cancelled"
    OFFER_ACCEPTED = "offer_accepted"
    PAUSE_SCHEDULED = "pause_scheduled"
    PAUSE_STARTED = "pause_started"
    RESUMED = "resumed"
    WIN_BACK_SENT = "win_back_sent"


class WinBackStage(StrEnum):
    """The win-back message after a cancellation: on day 14, then day 30."""

    DAY_14 = "day_14"
    DAY_30 = "day_30"


class PauseUnavailableReason(StrEnum):
    """
    Why a business cannot pause now: the platform has not turned pausing
    on yet (FEATURE_OFF), the subscription is not active and paid
    (NOT_ACTIVE: a trial, an unpaid or cancelled one), it is billed
    yearly (NOT_MONTHLY), a pause is already scheduled or running
    (ALREADY_PAUSED), or four months of the last twelve are used
    (ALLOWANCE_USED).
    """

    FEATURE_OFF = "feature_off"
    NOT_ACTIVE = "not_active"
    NOT_MONTHLY = "not_monthly"
    ALREADY_PAUSED = "already_paused"
    ALLOWANCE_USED = "allowance_used"
