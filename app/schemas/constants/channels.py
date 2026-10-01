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
