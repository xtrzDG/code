"""Owner cabinet: rating a conversation and writing to the customer."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.conversations import ConversationRating, StaffMessageDelivery
from app.schemas.dto.conversation_feed.conversation_views import MessageView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.booleans import SendAsTemplate
from app.schemas.typings.conversations.constrained_strings import StaffReplyText
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.users.prefixed_id import UserId


class ConversationRatingRequest(ImmutableDTO):
    """HTTP body of rating a conversation; null clears the rating."""

    rating: ConversationRating | None


class RateConversationCommand(ImmutableDTO):
    """Owner or staff rates how the assistant handled a conversation."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    rating: ConversationRating | None


class StaffMessageRequest(ImmutableDTO):
    """
    HTTP body of a staff message to the customer of a conversation;
    `as_template` sends it in the WhatsApp template the card offers once the
    24-hour window has closed (while the window is open it travels as an
    ordinary message).
    """

    text: StaffReplyText
    as_template: SendAsTemplate = False


class SendStaffMessageCommand(ImmutableDTO):
    """An owner or staff member writes to the customer from the cabinet."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    text: StaffReplyText
    as_template: SendAsTemplate = False
    client_ip_address: ClientIpAddress | None = None


class StaffMessageResult(ImmutableDTO):
    """The stored staff message and how it reaches the customer."""

    message: MessageView
    delivery: StaffMessageDelivery
