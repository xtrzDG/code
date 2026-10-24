from contextlib import AbstractContextManager

from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.phone_numbers import PhoneLineLockRegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

PHONE_LINE_LOCK_PURPOSE: str = "phone-line"
# The block rents a number and imports it (a few seconds at the carrier and
# the voice platform, each request bounded by its timeout).
PHONE_LINE_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(45)


class PhoneLineLockRegistry(PhoneLineLockRegistryContract):
    """
    One lock per business around changes of its phone line, so two clicks
    (two tabs, two instances) never rent two numbers, and a number is never
    given back while it is being taken.

    Session-held (`hold_with_session`): the block calls the carrier and the
    voice platform, and each storage write in it commits on its own, so a
    rented number is on record even when a later step fails.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_session(
            AdvisoryLockKey(f"{PHONE_LINE_LOCK_PURPOSE}|{business_id}"),
            PHONE_LINE_LOCK_WAIT,
        )
