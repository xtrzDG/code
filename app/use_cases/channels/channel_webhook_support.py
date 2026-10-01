"""Steps shared by the webhook use cases of messaging channels."""

import logging

from typed_time_provider import Microseconds

from app.contracts.channels import ChannelMessageReceiptRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import (
    ChannelDeliveryTarget,
    ChannelInboundDelivery,
    ChannelInboundMessage,
)
from app.schemas.dto.conversations import InboundMessage
from app.utilities.channels.delivery_targets import build_delivery_target

logger: logging.Logger = logging.getLogger(__name__)


def accept_inbound_message(
    message: ChannelInboundMessage,
    channel: ChannelDocument,
    secret_cipher: SecretCipherAdapterContract,
    receipt_repo: ChannelMessageReceiptRepoContract,
    now: Microseconds,
) -> ChannelInboundDelivery | None:
    """
    Turn a parsed message into the engine's InboundMessage for the business
    that owns `channel` (resolved on the server, never from the payload's
    words). A message the platform delivered before is skipped.
    """

    target: ChannelDeliveryTarget = build_delivery_target(
        channel,
        message.channel_user_id,
        secret_cipher,
    )
    if message.provider_message_id is not None and not receipt_repo.record_if_new(
        ChannelMessageReceiptDocument(
            business_id=channel.business_id,
            channel=channel.kind,
            provider_message_id=message.provider_message_id,
            created_at=now,
            updated_at=now,
        )
    ):
        logger.info(
            "Skipped a repeated %s delivery of message %s.",
            channel.kind.value,
            message.provider_message_id,
        )
        return None

    return ChannelInboundDelivery(
        message=InboundMessage(
            business_id=channel.business_id,
            channel=channel.kind,
            channel_user_id=message.channel_user_id,
            text=message.text,
            contact_name=message.contact_name,
            contact_phone_number=message.contact_phone_number,
        ),
        target=target,
    )
