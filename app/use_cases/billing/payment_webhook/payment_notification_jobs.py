"""
The queued job that applies a verified payment notification (API-03): the
webhook verifies the delivery, queues the event and answers at once; a
worker applies it. The jobs of one payment order run one at a time, oldest
first (their serial key), so the provider's order of delivery is kept.
"""

from pydantic import ValidationError

from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.dto.payment_webhooks import QueuedPaymentNotification
from app.schemas.dto.payments import VerifiedPaymentEvent
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson

APPLY_PAYMENT_NOTIFICATION_JOB: JobName = JobName("apply_payment_notification")
SERIAL_KEY_PREFIX: str = "payment_order:"


def payment_order_serial_key(payment_order_id: PaymentOrderId) -> JobSerialKey:
    """One payment order's notifications are applied one at a time, in order."""

    return JobSerialKey(f"{SERIAL_KEY_PREFIX}{payment_order_id}")


def encode_payment_notification(
    payment_order_id: PaymentOrderId,
    event: VerifiedPaymentEvent,
    secret_cipher: SecretCipherAdapterContract,
) -> JobPayloadJson:
    return JobPayloadJson(
        QueuedPaymentNotification(
            payment_order_id=payment_order_id,
            sealed_event=secret_cipher.encrypt(ChannelSecret(event.model_dump_json())),
        ).model_dump_json()
    )


def decode_payment_notification(
    payload: JobPayloadJson,
    secret_cipher: SecretCipherAdapterContract,
) -> tuple[PaymentOrderId, VerifiedPaymentEvent]:
    """
    Raises:
        ValidationFailedError: the payload is not a sealed payment
            notification of this platform (no key of the ring opens it).
    """

    try:
        queued = QueuedPaymentNotification.model_validate_json(str(payload))
        event = VerifiedPaymentEvent.model_validate_json(
            str(secret_cipher.decrypt(queued.sealed_event))
        )
    except ValidationError as error:
        raise ValidationFailedError(
            "The job payload is not a queued payment notification."
        ) from error

    return queued.payment_order_id, event
