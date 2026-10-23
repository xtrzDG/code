from enum import StrEnum


class PaymentProvider(StrEnum):
    """
    Payment service that charges owners: Flitt (concept: auto-debit) in
    Georgia and Armenia, Stripe in the EU, the US and Israel
    (`PaymentProviderRegistry`). STRIPE is stored only once the
    `stripe_payments` release gate opens.
    """

    FLITT = "flitt"
    STRIPE = "stripe"


class PaymentOrderPurpose(StrEnum):
    """
    What a payment order is for. CHECKOUT pays the open invoices and starts
    the automatic charges; CARD_SETUP charges nothing now and saves the card
    for the automatic charges (the trial's "Save card", "Update card").
    """

    CHECKOUT = "checkout"
    CARD_SETUP = "card_setup"


class PaymentRetryOutcome(StrEnum):
    """
    How one retry of a declined automatic charge went. CLAIMED: a worker
    took it and is charging; APPROVED and DECLINED: the provider's answer
    (its notification settles the invoice); PROCESSING: the answer comes
    by notification; FAILED: the provider could not be reached or refused
    the request; NOT_POSSIBLE: nothing to charge again with (no saved card
    or provider charge); SKIPPED: a later retry was due by the time the job
    ran, so this one was never charged.
    """

    CLAIMED = "claimed"
    APPROVED = "approved"
    DECLINED = "declined"
    PROCESSING = "processing"
    FAILED = "failed"
    NOT_POSSIBLE = "not_possible"
    SKIPPED = "skipped"


class DunningNoticeKind(StrEnum):
    """What the owners are told after a retry of a declined charge."""

    RETRY_DECLINED = "retry_declined"
    LAST_RETRY_DECLINED = "last_retry_declined"
    PAYMENT_RECOVERED = "payment_recovered"


class PaymentStatus(StrEnum):
    """
    Status of a payment as the provider reports it (Flitt `order_status`).

    APPROVED pays the invoices; DECLINED fails them; EXPIRED means the owner
    left the payment page unpaid; REVERSED is a refund of an approved payment.
    """

    CREATED = "created"
    PROCESSING = "processing"
    APPROVED = "approved"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVERSED = "reversed"


class PaymentWebhookOutcome(StrEnum):
    """What processing one provider notification did."""

    APPLIED = "applied"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"
    REFUND_DUE = "refund_due"
