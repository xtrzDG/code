"""The pause of the migration runner between two tries of one file."""

import secrets
import time
from collections.abc import Callable

from app.contracts.storage import MigrationRetryPauseContract
from app.schemas.typings.storage.constrained_integers import MigrationAttemptNumber

DEFAULT_FIRST_PAUSE_SECONDS: float = 1.0
DEFAULT_LONGEST_PAUSE_SECONDS: float = 16.0
SYSTEM_RANDOM: secrets.SystemRandom = secrets.SystemRandom()


class JitteredMigrationRetryPause(MigrationRetryPauseContract):
    """
    Exponential backoff with equal jitter: the pause after try n is drawn
    from [d/2, d] with d = first * 2^(n-1), at most `longest_seconds`, so
    runners that lost the same lock do not come back in step and each try
    gives the live release's long transaction time to finish (1 s, 2 s,
    4 s, 8 s by default: at most about 15 s between five tries).
    """

    def __init__(
        self,
        first_seconds: float = DEFAULT_FIRST_PAUSE_SECONDS,
        longest_seconds: float = DEFAULT_LONGEST_PAUSE_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        random_fraction: Callable[[], float] = SYSTEM_RANDOM.random,
    ) -> None:
        self._first_seconds: float = first_seconds
        self._longest_seconds: float = longest_seconds
        self._sleep: Callable[[float], None] = sleep
        self._random_fraction: Callable[[], float] = random_fraction

    def pause(self, attempt: MigrationAttemptNumber) -> None:
        self._sleep(self.seconds_after(attempt))

    def seconds_after(self, attempt: MigrationAttemptNumber) -> float:
        ceiling: float = min(
            self._longest_seconds,
            self._first_seconds * 2 ** (int(attempt) - 1),
        )
        return ceiling / 2 + ceiling / 2 * self._random_fraction()
