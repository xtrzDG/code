from contextlib import AbstractContextManager

from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.monitoring import PlatformAlertLockRegistryContract
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

PLATFORM_ALERT_LOCK_KEY: AdvisoryLockKey = AdvisoryLockKey("platform-alert-states")
# A look reads a few keyed rows and writes a few: a holder is done within
# a second. A process that still waits after this long skips its turn.
PLATFORM_ALERT_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(10)


class PlatformAlertLockRegistry(PlatformAlertLockRegistryContract):
    """
    One lock over the platform alerts' episodes and the watchers' marks,
    held for the block's transaction (`hold_with_transaction`): the
    workers' `platform_alerts` job and the API's pipeline watchdog decide
    an episode's next step only under it, so one start of an episode is
    told once, however many processes look at the same moment.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_states(self) -> AbstractContextManager[None]:
        return self._advisory_locks.hold_with_transaction(
            PLATFORM_ALERT_LOCK_KEY, PLATFORM_ALERT_LOCK_WAIT
        )
