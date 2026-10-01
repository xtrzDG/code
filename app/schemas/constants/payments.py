from enum import StrEnum


class PaymentProvider(StrEnum):
    """Payment service that charges owners (concept: Flitt with auto-debit)."""

    FLITT = "flitt"


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
