import logging
from collections.abc import Mapping

from typed_time_provider import Microseconds

from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.schemas.dto.rate_limits import RateLimitCounter, RateLimitWindow
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.calls.zadarma_notifications import (
    call_id_digest,
    signed_content_digest,
)
from app.utilities.limits.sliding_window_limits import locate_window
from app.utilities.monitoring.signal_windows import UNLIMITED

LOGGER: logging.Logger = logging.getLogger(__name__)

KEY_PREFIX: str = "zadarma-notification"
ONCE: RequestsPerWindow = RequestsPerWindow(1)
MICROSECONDS_PER_SECOND: int = 1_000_000
# The claims sit in the window of `call_start` (not of their arrival), so
# every copy of a notification meets the same claim; the window's counter
# lives until the end of the next one, past the oldest accepted copy.
CLAIM_WINDOW_SECONDS: RateWindowSeconds = RateWindowSeconds(24 * 60 * 60)


class ZadarmaReplayGuard:
    """
    Telling a copy of a signed Zadarma notification from the original, in
    the shared rate-limit buckets (every API process sees the same claims).

    The signature covers who called, which number and when, not the call
    id: a copy with another `pbx_call_id` would pass the signature and make
    a second missed call and text-back. The signed fields are claimed once;
    the call ids seen with them are counted. A copy of those fields with a
    call id never seen with them is a replay. The very same notification
    again is not: it is the provider's retry, and the missed call it names
    already exists (answered "duplicate" by its own id).

    A claim that cannot be read or written is logged and the notification
    handled: the missed call's own id still keeps exact repeats out.
    """

    def __init__(self, buckets: RateLimitBucketAdapterContract) -> None:
        self._buckets: RateLimitBucketAdapterContract = buckets

    def is_replay(self, fields: Mapping[str, str], call_start_seconds: int) -> bool:
        window: RateLimitWindow = locate_window(
            Microseconds(call_start_seconds * MICROSECONDS_PER_SECOND),
            CLAIM_WINDOW_SECONDS,
        )
        content: str = signed_content_digest(fields)
        content_key = RateLimitKey(f"{KEY_PREFIX}:{content}")
        call_key = RateLimitKey(f"{KEY_PREFIX}:{content}:{call_id_digest(fields)}")
        try:
            seen_with_this_call: bool = (
                int(self._buckets.read_counts(call_key, window).current_count) > 0
            )
            self._buckets.count_if_within(
                [RateLimitCounter(key=call_key, limit=UNLIMITED)], window
            )
            is_first_copy: bool = (
                self._buckets.count_if_within(
                    [RateLimitCounter(key=content_key, limit=ONCE)], window
                )
                is None
            )
        except ApplicationError as error:
            LOGGER.warning("Zadarma notification not claimed: %s", error)
            return False

        return not is_first_copy and not seen_with_this_call
