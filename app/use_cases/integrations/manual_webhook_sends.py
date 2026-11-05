"""
The limit of the webhook requests an owner sends by hand ("Send test
event" and a retry from the delivery log): each one makes the platform
post to an outside address at once, so a script repeating them must not
turn the platform into a relay that floods someone's server.
"""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import RequestsPerWindow
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import refuse_over_limits

# Test events and retries a business may send by hand in a minute, together.
MANUAL_SENDS_PER_MINUTE: RequestsPerWindow = RequestsPerWindow(10)
MANUAL_SEND_KEY_PREFIX: str = "webhook-manual-send:business"
TOO_MANY_SENDS_MESSAGE: str = (
    "Too many test events and retries this minute; try again shortly."
)


def count_manual_send(
    rate_limits: RequestRateLimitRegistryContract,
    business_id: BusinessId,
    now: Microseconds,
) -> None:
    """
    Count one hand-sent webhook request of the business.

    Raises:
        RateLimitedError: MANUAL_SENDS_PER_MINUTE are used up (429 with
            Retry-After); nothing is sent then.
    """

    refuse_over_limits(
        rate_limits,
        [
            RateLimitCounter(
                key=RateLimitKey(f"{MANUAL_SEND_KEY_PREFIX}:{business_id}"),
                limit=MANUAL_SENDS_PER_MINUTE,
            )
        ],
        TOO_MANY_SENDS_MESSAGE,
        now,
    )
