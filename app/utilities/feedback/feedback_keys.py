"""
Identities of the feedback after visits: the settings of a business, the
request after a visit (one per booking), the outbox message that carries
it, the public token of a review link and the address it is opened at.
"""

import secrets
from uuid import UUID, uuid5

from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.schemas.typings.feedback.constrained_strings import (
    ReviewLinkToken,
    ReviewRedirectUrl,
)
from app.schemas.typings.feedback.prefixed_id import (
    FeedbackRequestId,
    ReviewSettingsId,
)

# Fixed namespaces of derived ids (never change them: stored ids depend on
# them).
REVIEW_SETTINGS_NAMESPACE: UUID = UUID("9b2f6e14-3c8a-4d51-a7e0-5f1c2b8d6a93")
FEEDBACK_REQUEST_NAMESPACE: UUID = UUID("d41e7a3c-8f25-4b96-b0c8-2e6a9f1d4c57")
# 16 random bytes: 22 base64url characters.
REVIEW_TOKEN_BYTES: int = 16
REVIEW_LINK_PATH: str = "/v1/public/reviews/"


def review_settings_id_of(business_id: BusinessId) -> ReviewSettingsId:
    """One settings document per business."""

    return ReviewSettingsId(uuid5(REVIEW_SETTINGS_NAMESPACE, str(business_id)))


def feedback_request_id_of(
    business_id: BusinessId,
    booking_id: BookingId,
) -> FeedbackRequestId:
    """A visit is asked about once: the same booking, the same request."""

    return FeedbackRequestId(
        uuid5(FEEDBACK_REQUEST_NAMESPACE, f"{business_id}|{booking_id}")
    )


def feedback_idempotency_key(request_id: FeedbackRequestId) -> OutboundIdempotencyKey:
    """One outbox message per request."""

    return OutboundIdempotencyKey(f"feedback:{request_id}")


def new_review_token() -> ReviewLinkToken:
    """A fresh, unguessable public token for one customer's review link."""

    return ReviewLinkToken(secrets.token_urlsafe(REVIEW_TOKEN_BYTES))


def review_redirect_url(
    app_base_url: PublicBaseUrl,
    token: ReviewLinkToken,
) -> ReviewRedirectUrl:
    """The platform's address of a review link (it counts, then redirects)."""

    return ReviewRedirectUrl(
        f"{str(app_base_url).rstrip('/')}{REVIEW_LINK_PATH}{token}"
    )
