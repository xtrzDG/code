"""Showing a customer "typing…" while their reply is being written."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import ChannelUserId


class TypingRequest(ImmutableDTO):
    """
    Whom to show "typing…": the customer in the business's connected
    channel, and the platform's id of the message being answered (the
    WhatsApp indicator goes with its read receipt).
    """

    business_id: BusinessId
    channel: ChannelKind
    channel_id: ChannelId | None = None
    channel_user_id: ChannelUserId
    replying_to: ProviderMessageId | None = None
