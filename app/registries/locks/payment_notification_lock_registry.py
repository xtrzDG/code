from contextlib import AbstractContextManager

from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.payment_locks import PaymentNotificationLockRegistryContract
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

PAYMENT_NOTIFICATION_LOCK_PURPOSE: str = "payment-notification"
# The holder may wait for the provider (a status read, a stop of charges,
# each within its own timeout): a copy waits longer than that, and the
# queued job of a copy that still finds the lock taken tries again.
PAYMENT_NOTIFICATION_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(45)


class PaymentNotificationLockRegistry(PaymentNotificationLockRegistryContract):
    """
    One lock per payment order (business|order) around applying a
    provider notification. Session-held (`hold_with_session`): the block
    may call the provider, so no storage transaction stays open meanwhile,
    and the order the holder stored is committed when the next holder
    reads it.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_for_order(
        self, business_id: BusinessId, payment_order_id: PaymentOrderId
    ) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_session(
            AdvisoryLockKey(
                f"{PAYMENT_NOTIFICATION_LOCK_PURPOSE}|{business_id}|{payment_order_id}"
            ),
            PAYMENT_NOTIFICATION_LOCK_WAIT,
        )
