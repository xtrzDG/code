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


class MessageDirection(StrEnum):
    """Direction of a stored message."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
