from enum import StrEnum


class ChannelKind(StrEnum):
    """Customer-facing channel the assistant answers in."""

    PHONE = "phone"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    MESSENGER = "messenger"
    TELEGRAM = "telegram"
    WEB_CHAT = "web_chat"
    VIBER = "viber"
    OWNER_TEST = "owner_test"


class ChannelStatus(StrEnum):
    """Connection state of a channel."""

    PENDING = "pending"
    CONNECTED = "connected"
    DISABLED = "disabled"
    ERROR = "error"


class ChannelLinkState(StrEnum):
    """
    Whether customers can be sent a link to a connected channel: LINKED when
    its public address (Telegram bot, WhatsApp number, Instagram or page
    username, phone number) is known; MISSING_PUBLIC_ADDRESS when the
    channel answers but the platform never told its public address (it was
    connected before addresses were learned): the share links skip it and
    reconnecting it once fixes that.
    """

    LINKED = "linked"
    MISSING_PUBLIC_ADDRESS = "missing_public_address"


class MessageDirection(StrEnum):
    """Direction of a stored message."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class WidgetPosition(StrEnum):
    """Corner of the page where the website chat launcher sits."""

    LEFT = "left"
    RIGHT = "right"
