"""A website visitor's thumbs up or down on the chat's answers."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.conversations import (
    ConversationRating,
    ConversationRatingReason,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.prefixed_id import MessageId


class WidgetRatingRequest(ImmutableDTO):
    """
    HTTP body of the visitor's rating of their own chat: good or bad, why
    it was bad (optional) and the answer it is about (the latest answer
    when not named).
    """

    session_key: WidgetSessionKey
    rating: ConversationRating
    reason: ConversationRatingReason | None = None
    message_id: MessageId | None = None


class WidgetRatingCommand(ImmutableDTO):
    """A visitor's rating for one business's widget, and where it came from."""

    business_id: BusinessId
    request: WidgetRatingRequest
    client_ip_address: ClientIpAddress | None = None


class WidgetRatingView(ImmutableDTO):
    """The rating the widget shows as given (whether or not the team's stands)."""

    rating: ConversationRating
    reason: ConversationRatingReason | None = None
