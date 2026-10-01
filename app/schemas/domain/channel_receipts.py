from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelMessageReceiptId
from app.schemas.typings.channels.strings import ProviderMessageId


class ChannelMessageReceiptDocument(BaseDocument):
    """
    A customer message already handed to the assistant.

    Messaging platforms redeliver a webhook when the first delivery timed out;
    the receipt turns the repeated delivery into a no-op instead of a second
    answer. One receipt per business, channel and provider message id.
    """

    id: ChannelMessageReceiptId = Field(default_factory=ChannelMessageReceiptId)
    business_id: BusinessId
    channel: ChannelKind
    provider_message_id: ProviderMessageId
