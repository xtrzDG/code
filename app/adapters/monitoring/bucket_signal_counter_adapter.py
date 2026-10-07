import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.monitoring import SignalCounterAdapterContract
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.platform_alerts import SignalTally
from app.schemas.dto.rate_limits import (
    RateLimitBucketCounts,
    RateLimitCounter,
    RateLimitWindow,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.monitoring.constrained_integers import SignalEventCount
from app.utilities.limits.sliding_window_limits import locate_window
from app.utilities.monitoring.signal_windows import (
    SIGNAL_WINDOW_SECONDS,
    UNLIMITED,
    signal_key,
)

logger: logging.Logger = logging.getLogger(__name__)


class BucketSignalCounterAdapter(SignalCounterAdapterContract):
    """
    Platform signals counted in the rate-limit buckets (migration 1041):
    one bucket per signal and fixed window of SIGNAL_WINDOW_SECONDS, with a
    limit no count reaches, so every process adds to the same row and the
    alerts job reads it. The buckets are swept with the rate limits'
    (`sweep_rate_limit_buckets`); the table is UNLOGGED, so a database
    crash only empties the windows of the moment.

    A count that cannot be written is logged and dropped: counting never
    fails the model call or the login it describes.
    """

    def __init__(
        self,
        buckets: RateLimitBucketAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._buckets: RateLimitBucketAdapterContract = buckets
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def count(self, signal: PlatformSignal) -> None:
        window: RateLimitWindow = locate_window(
            self._wall_clock.now_unix(), SIGNAL_WINDOW_SECONDS
        )
        try:
            self._buckets.count_if_within(
                [RateLimitCounter(key=signal_key(signal), limit=UNLIMITED)], window
            )
        except ApplicationError as error:
            logger.warning("Platform signal %s was not counted: %s", signal, error)

    def read(self, signal: PlatformSignal, now: Microseconds) -> SignalTally:
        counts: RateLimitBucketCounts = self._buckets.read_counts(
            signal_key(signal), locate_window(now, SIGNAL_WINDOW_SECONDS)
        )
        return SignalTally(
            signal=signal,
            current=SignalEventCount(int(counts.current_count)),
            previous=SignalEventCount(int(counts.previous_count)),
        )
