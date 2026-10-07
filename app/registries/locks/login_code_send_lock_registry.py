from contextlib import AbstractContextManager

from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.registries import LoginCodeSendLockRegistryContract
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

LOGIN_CODE_SEND_LOCK_KEY: AdvisoryLockKey = AdvisoryLockKey("login code sends")
# The section reads the last hour's challenges and stores one.
LOGIN_CODE_SEND_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(10)


class LoginCodeSendLockRegistry(LoginCodeSendLockRegistryContract):
    """
    One platform-wide lock for the check-and-reserve step of login code
    sends: the hourly caps are checked against the stored challenges and
    the new challenge is stored under it, in every API instance alike, so
    parallel requests cannot all pass the caps. The lock is
    transaction-held: the reservation is committed when the next request
    counts the challenges.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock(self) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_transaction(
            LOGIN_CODE_SEND_LOCK_KEY,
            LOGIN_CODE_SEND_LOCK_WAIT,
        )
