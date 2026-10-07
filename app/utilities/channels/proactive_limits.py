"""
The daily caps of messages a customer did not ask for (reminders,
feedback requests, messages after a missed call): every proactive message
to one customer counts against one shared counter, so no customer gets
more than a few a day whatever sends them; each kind may add its own.
"""

import hashlib

from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey

PROACTIVE_WINDOW: RateWindowSeconds = RateWindowSeconds(24 * 60 * 60)
# A reminder, a feedback request and a message after a missed call fit; a
# fourth message the same day does not go out.
PROACTIVE_DAILY_LIMIT: RequestsPerWindow = RequestsPerWindow(3)
KEY_DIGEST_LENGTH: int = 32


def proactive_message_counter(
    business_id: BusinessId,
    contact_id: ContactId,
) -> RateLimitCounter:
    """The shared daily counter of one customer's unrequested messages."""

    digest: str = hashlib.sha256(f"{business_id}|{contact_id}".encode()).hexdigest()[
        :KEY_DIGEST_LENGTH
    ]
    return RateLimitCounter(
        key=RateLimitKey(f"proactive:contact:{digest}"),
        limit=PROACTIVE_DAILY_LIMIT,
    )
