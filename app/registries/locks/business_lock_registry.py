from contextlib import AbstractContextManager

from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.operations import BusinessLockRegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

BOOKING_LOCK_PURPOSE: str = "bookings"
# The locked section re-reads the bookings of a day and writes one: well
# under a second. A wait this long means a stuck holder.
BOOKING_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(10)


class BusinessLockRegistry(BusinessLockRegistryContract):
    """
    One lock per business around the availability re-check and the booking
    write, so two customers (in any API instance or worker) cannot take the
    last unit at the same moment.

    The lock is transaction-held (`hold_with_transaction`): the booking
    written in the block is committed when the next holder starts its own
    re-check.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_transaction(
            AdvisoryLockKey(f"{BOOKING_LOCK_PURPOSE}|{business_id}"),
            BOOKING_LOCK_WAIT,
        )
