"""
Declined payments per business (LOG-05, card testing): someone who tests
stolen cards opens the platform's payment pages (checkout, "Save card")
again and again, and the provider declines most of the cards. Each
declined payment of a business (not a retry of a declined automatic
charge, which the dunning job makes itself) counts in the business's
hourly bucket, shared by every process; the declines of the window
filling now and the one before (one to two hours) are what counts.

- The ALERT_DECLINES-th counts the platform signal
  `tenant_payment_declines` (the alert of the same name), with a warning
  line that names the business.
- From BRAKE_DECLINES on, the business opens no new payment page (429
  with Retry-After) until the windows cool down, and the signal counts
  again: the burst can test only so many cards. An owner whose own card
  was declined a few times is far below either.
"""

import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.monitoring import SignalCounterAdapterContract
from app.contracts.payment_declines import PaymentDeclineWatchFacilitatorContract
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.rate_limits import (
    RateLimitBucketCounts,
    RateLimitCounter,
    RateLimitWindow,
)
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RetryAfterSeconds,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import locate_window
from app.utilities.monitoring.signal_windows import UNLIMITED

LOGGER: logging.Logger = logging.getLogger(__name__)
HOUR: RateWindowSeconds = RateWindowSeconds(60 * 60)
ALERT_DECLINES: int = 5
BRAKE_DECLINES: int = 10
KEY_PREFIX: str = "tenant-payment-declines:"


class PaymentDeclineWatchFacilitator(PaymentDeclineWatchFacilitatorContract):
    """Declines counted per business and hour, alerted at 5, braked at 10."""

    def __init__(
        self,
        buckets: RateLimitBucketAdapterContract,
        signal_counter: SignalCounterAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._buckets: RateLimitBucketAdapterContract = buckets
        self._signals: SignalCounterAdapterContract = signal_counter
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def record_decline(self, business_id: BusinessId) -> None:
        try:
            key: RateLimitKey = decline_key(business_id)
            window: RateLimitWindow = locate_window(self._wall_clock.now_unix(), HOUR)
            self._buckets.count_if_within(
                [RateLimitCounter(key=key, limit=UNLIMITED)], window
            )
            declines: int = recent_declines(self._buckets.read_counts(key, window))
            if declines == ALERT_DECLINES:
                self._signals.count(PlatformSignal.TENANT_PAYMENT_DECLINES)
                LOGGER.warning(
                    "Business %s had %s payments declined within two hours",
                    business_id,
                    declines,
                )
            elif declines == BRAKE_DECLINES:
                self._signals.count(PlatformSignal.TENANT_PAYMENT_DECLINES)
                LOGGER.warning(
                    "Business %s had %s payments declined within two hours: it "
                    "opens no new payment page until they cool down",
                    business_id,
                    declines,
                )
        except Exception:
            LOGGER.exception(
                "A declined payment of business %s was not counted.", business_id
            )

    def require_payment_pages(self, business_id: BusinessId) -> None:
        window: RateLimitWindow = locate_window(self._wall_clock.now_unix(), HOUR)
        declines: int = recent_declines(
            self._buckets.read_counts(decline_key(business_id), window)
        )
        if declines >= BRAKE_DECLINES:
            LOGGER.warning(
                "A payment page of business %s was refused: %s declines "
                "within two hours",
                business_id,
                declines,
            )
            raise RateLimitedError(
                "Too many payments of this business were declined in the last "
                "hour; a new payment page can be opened later.",
                retry_after_seconds=RetryAfterSeconds(int(HOUR)),
            )


def decline_key(business_id: BusinessId) -> RateLimitKey:
    return RateLimitKey(f"{KEY_PREFIX}{business_id}")


def recent_declines(counts: RateLimitBucketCounts) -> int:
    """The declines of the window filling now and the one before it."""

    return int(counts.current_count) + int(counts.previous_count)
