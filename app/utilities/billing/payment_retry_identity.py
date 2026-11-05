"""
Ids of the retries of a declined automatic charge: derived (UUID v5) from
the unpaid invoice and the attempt, so every worker that reaches a retry
names the same row and only one of them claims it.
"""

from uuid import UUID, uuid5

from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.billing.prefixed_id import InvoiceId, PaymentRetryId

PAYMENT_RETRY_NAMESPACE: UUID = UUID("f07f4c28-82e2-4caa-887d-a5ea2f3ac213")


def derive_payment_retry_id(
    invoice_id: InvoiceId, attempt: PaymentRetryAttempt
) -> PaymentRetryId:
    return PaymentRetryId(
        uuid5(PAYMENT_RETRY_NAMESPACE, f"{invoice_id}|{int(attempt)}")
    )


def parse_payment_retry_id(reference: object) -> PaymentRetryId | None:
    """The retry id a provider order reference carries, if it is one."""

    try:
        return PaymentRetryId(str(reference))
    except TypeError, ValueError:
        return None
