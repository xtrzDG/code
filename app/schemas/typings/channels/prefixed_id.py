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


class WidgetVisitorId(BasePrefixedTypedId):
    """
    A website chat visitor as the live stream names them: derived from the
    widget's visitor key (one-way, `widget_visitor_id`), so live events and
    stream tickets name the visitor without carrying the key itself.
    """

    prefix = "widget_visitor"
    uuid_version = None


# Keep abc order for all non example types, if possible.
