import logging

from typed_time_provider import Microseconds

from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.schemas.dto.rate_limits import (
    RateLimitBucketCounts,
    RateLimitCounter,
    RateLimitWindow,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import locate_window

LOGGER: logging.Logger = logging.getLogger(__name__)

KEY_PREFIX: str = "twilio-webhook"
ONCE: RequestsPerWindow = RequestsPerWindow(1)
# A claim is seen for this long at least (its window and the next one).
CLAIM_WINDOW_SECONDS: RateWindowSeconds = RateWindowSeconds(24 * 60 * 60)


class TwilioReplayGuard:
    """
    Telling a copy of a signed Twilio request from the original, in the
    shared rate-limit buckets (every API process sees the same claims).

    `X-Twilio-Signature` carries no time, so a captured fallback or dial
    status request stays valid: sent again it would ring the staff mobile,
    store a missed call and alert the owner again. Its claim
    (`describe_request_claim`: the address, the call and its status) is
    taken once; a request whose claim was taken in this window or the one
    before (at least 24 hours) is a replay.

    A claim that cannot be read or written is logged and the request
    handled: the missed call's own id still keeps exact repeats out.
    """

    def __init__(self, buckets: RateLimitBucketAdapterContract) -> None:
        self._buckets: RateLimitBucketAdapterContract = buckets

    def is_replay(self, claim: str, now: Microseconds) -> bool:
        key = RateLimitKey(f"{KEY_PREFIX}:{claim}")
        window: RateLimitWindow = locate_window(now, CLAIM_WINDOW_SECONDS)
        try:
            counts: RateLimitBucketCounts = self._buckets.read_counts(key, window)
            if int(counts.current_count) > 0 or int(counts.previous_count) > 0:
                return True

            refused: RateLimitKey | None = self._buckets.count_if_within(
                [RateLimitCounter(key=key, limit=ONCE)], window
            )
        except ApplicationError as error:
            LOGGER.warning("Twilio request not claimed: %s", error)
            return False

        # Another process took the claim between the read and the count.
        return refused is not None
