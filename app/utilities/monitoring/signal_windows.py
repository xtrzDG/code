"""
The shared windows platform signals are counted in (model calls, failed
model calls, refused login codes): fixed windows of SIGNAL_WINDOW_MINUTES
in the rate-limit buckets every process writes. A rate alert reads the
window filling now together with the one before (15 to 30 minutes of
traffic), so its figure does not drop to nothing when a window starts.
"""

from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.typings.monitoring.constrained_integers import AlertWindowMinutes
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey

SIGNAL_WINDOW_MINUTES: AlertWindowMinutes = AlertWindowMinutes(15)
SIGNAL_WINDOW_SECONDS: RateWindowSeconds = RateWindowSeconds(
    int(SIGNAL_WINDOW_MINUTES) * 60
)
# A counter is a rate-limit bucket that never refuses: the largest limit.
UNLIMITED: RequestsPerWindow = RequestsPerWindow(10_000_000)
SIGNAL_KEY_PREFIX: str = "platform-signal:"


def signal_key(signal: PlatformSignal) -> RateLimitKey:
    """The bucket key every process counts the signal under."""

    return RateLimitKey(f"{SIGNAL_KEY_PREFIX}{signal.value}")
