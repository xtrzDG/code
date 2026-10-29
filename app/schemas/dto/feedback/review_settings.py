"""Settings → Reviews: feedback after visits and the Google review link."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.booleans import IsChannelConnected
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.feedback.booleans import (
    IsReviewLinkTracked,
    IsVisitFeedbackEnabled,
)
from app.schemas.typings.feedback.constrained_integers import FeedbackDelayMinutes
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId

DEFAULT_DELAY_MINUTES: FeedbackDelayMinutes = FeedbackDelayMinutes(120)


class ReviewSettingsRequest(ImmutableDTO):
    """
    The owner's choices: ask customers how their visit went
    (`delay_minutes` after it ended), the approved WhatsApp template for a
    closed 24-hour window, and the Google review page everyone who answers
    is invited to (the profile's link of kind `google_review`).
    """

    is_feedback_enabled: IsVisitFeedbackEnabled = False
    delay_minutes: FeedbackDelayMinutes = DEFAULT_DELAY_MINUTES
    feedback_template_name: WhatsAppTemplateName | None = None
    google_review_url: WebLink | None = None


class ReviewSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class UpdateReviewSettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: ReviewSettingsRequest


class FeedbackTemplatePreview(ImmutableDTO):
    """
    The feedback request in one language: the body to register as the
    WhatsApp template (its one parameter {{1}} is the business name) and
    how a customer reads it.
    """

    language: LanguageTag
    template_body: MessageText
    example: MessageText


class ReviewSettingsView(ImmutableDTO):
    """
    The settings with what they rely on: whether the business's WhatsApp
    number is connected (the template), whether review-link visits can be
    counted (the platform's public address is set), and the request in
    each language of the business.
    """

    is_feedback_enabled: IsVisitFeedbackEnabled
    delay_minutes: FeedbackDelayMinutes
    feedback_template_name: WhatsAppTemplateName | None = None
    google_review_url: WebLink | None = None
    is_whatsapp_connected: IsChannelConnected
    is_link_tracked: IsReviewLinkTracked
    template_previews: list[FeedbackTemplatePreview] = Field(
        default_factory=list[FeedbackTemplatePreview]
    )
