"""
The daily caps of feedback requests: one per customer a day (two visits
the same day are asked about once), the shared cap of every unrequested
message to a customer, and a cap per business (each request outside the
messaging window costs a WhatsApp template; a flood is abuse).
"""

import hashlib

from app.schemas.constants.feedback import FeedbackSkipReason
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.proactive_limits import proactive_message_counter

FEEDBACK_WINDOW: RateWindowSeconds = RateWindowSeconds(24 * 60 * 60)
CUSTOMER_FEEDBACK_DAILY_LIMIT: RequestsPerWindow = RequestsPerWindow(1)
BUSINESS_FEEDBACK_DAILY_LIMIT: RequestsPerWindow = RequestsPerWindow(500)
KEY_DIGEST_LENGTH: int = 32


def customer_feedback_key(
    business_id: BusinessId, contact_id: ContactId
) -> RateLimitKey:
    """The counter of feedback requests to one customer (a digest, no id in it)."""

    digest: str = hashlib.sha256(f"{business_id}|{contact_id}".encode()).hexdigest()[
        :KEY_DIGEST_LENGTH
    ]
    return RateLimitKey(f"feedback:contact:{digest}")


def business_feedback_key(business_id: BusinessId) -> RateLimitKey:
    return RateLimitKey(f"feedback:business:{business_id}")


def feedback_counters(
    business_id: BusinessId,
    contact_id: ContactId,
) -> list[RateLimitCounter]:
    return [
        RateLimitCounter(
            key=customer_feedback_key(business_id, contact_id),
            limit=CUSTOMER_FEEDBACK_DAILY_LIMIT,
        ),
        proactive_message_counter(business_id, contact_id),
        RateLimitCounter(
            key=business_feedback_key(business_id),
            limit=BUSINESS_FEEDBACK_DAILY_LIMIT,
        ),
    ]


def refusal_reason(
    business_id: BusinessId,
    contact_id: ContactId,
    refused_key: RateLimitKey,
) -> FeedbackSkipReason:
    """Asked today about another visit, or a daily cap was reached."""

    if refused_key == customer_feedback_key(business_id, contact_id):
        return FeedbackSkipReason.ALREADY_ASKED

    return FeedbackSkipReason.DAILY_LIMIT
