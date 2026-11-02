from enum import StrEnum


class PaymentMismatchKind(StrEnum):
    """
    How a payment's status at its provider (Flitt, Stripe) differs from the
    platform's record of it, found by the daily reconciliation:

    - PAID_AT_PROVIDER: the provider took the money, the platform has the
      payment unpaid (a lost notification: the owner paid and is dunned);
    - FAILED_AT_PROVIDER: the provider declined or let the payment expire,
      the platform has it paid (the owner uses the service unpaid);
    - REVERSED_AT_PROVIDER: the provider refunded or charged the payment
      back, the platform has it paid;
    - RENEWAL_PAID_AT_PROVIDER: Stripe charged a renewal of the order's
      subscription that the platform never recorded (a lost notification:
      the owner paid and may be dunned).
    """

    PAID_AT_PROVIDER = "paid_at_provider"
    FAILED_AT_PROVIDER = "failed_at_provider"
    REVERSED_AT_PROVIDER = "reversed_at_provider"
    RENEWAL_PAID_AT_PROVIDER = "renewal_paid_at_provider"
