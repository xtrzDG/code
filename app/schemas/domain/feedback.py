from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import FeedbackRequestStatus, FeedbackSkipReason
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.feedback.booleans import IsVisitFeedbackEnabled
from app.schemas.typings.feedback.constrained_integers import (
    FeedbackDelayMinutes,
    ReviewLinkClickCount,
    VisitScore,
)
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken
from app.schemas.typings.feedback.prefixed_id import (
    FeedbackRequestId,
    ReviewSettingsId,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag

DEFAULT_FEEDBACK_DELAY: FeedbackDelayMinutes = FeedbackDelayMinutes(120)


class ReviewSettingsDocument(BaseDocument):
    """
    Feedback after visits for one business (Settings → Reviews; one
    document per business, the id derived from it).

    With `is_feedback_enabled`, a customer whose visit ended
    `delay_minutes` ago is asked in their messenger and language how it
    went (1 to 5). Where the 24-hour messaging window is closed, WhatsApp
    carries the approved template `feedback_template_name`. The Google
    review link everyone who answers gets is the profile's link of kind
    `google_review`. Without a document: off.
    """

    id: ReviewSettingsId
    business_id: BusinessId
    is_feedback_enabled: IsVisitFeedbackEnabled = False
    delay_minutes: FeedbackDelayMinutes = DEFAULT_FEEDBACK_DELAY
    feedback_template_name: WhatsAppTemplateName | None = None


class FeedbackRequestDocument(BaseDocument):
    """
    The request for feedback after one visit (a booking) and how it went.

    The id derives from the business and the booking, so a visit is asked
    about once. A SENT request went into the outbox (`outbound_message_id`)
    in `channel` and `language` and waits for the customer's rating; the
    outbox marks it delivered (`delivered_at`) or FAILED. The rating
    (`score`) makes it ANSWERED; a low one also opened a handoff
    (`handoff_id`). Everyone who answers gets the business's review link
    through the platform's address with `review_token`, which counts the
    customer's visits (`review_clicks`). A SKIPPED request keeps why
    (`skip_reason`). No text the customer wrote is kept here: their words
    stay in the conversation, which an erasure removes.
    """

    id: FeedbackRequestId
    business_id: BusinessId
    booking_id: BookingId
    contact_id: ContactId
    visit_ended_at: Microseconds
    language: LanguageTag
    status: FeedbackRequestStatus
    skip_reason: FeedbackSkipReason | None = None
    channel: ChannelKind | None = None
    conversation_id: ConversationId | None = None
    outbound_message_id: OutboundMessageId | None = None
    review_token: ReviewLinkToken | None = None
    sent_at: Microseconds | None = None
    delivered_at: Microseconds | None = None
    last_error: DeliveryErrorText | None = None
    score: VisitScore | None = None
    answered_at: Microseconds | None = None
    handoff_id: HandoffId | None = None
    review_clicks: ReviewLinkClickCount = ReviewLinkClickCount(0)
    first_clicked_at: Microseconds | None = None
