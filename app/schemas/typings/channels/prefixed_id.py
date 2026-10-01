"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class ChannelId(BasePrefixedTypedId):
    """Random identifier of a connected channel."""

    prefix = "channel"


class ChannelMessageReceiptId(BasePrefixedTypedId):
    """Random identifier of a processed-message receipt."""

    prefix = "channel_message_receipt"


class ManagerTelegramLinkId(BasePrefixedTypedId):
    """Random identifier of a pending staff Telegram link."""

    prefix = "manager_telegram_link"


# Keep abc order for all non example types, if possible.
