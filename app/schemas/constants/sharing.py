"""Sharing the assistant: the hosted chat page, channel links and QR codes."""

from enum import StrEnum


class ShareLinkKind(StrEnum):
    """
    A way customers start a conversation from a shared link or QR code: the
    hosted chat page, a messenger chat (WhatsApp, Telegram, Messenger,
    Instagram) or a phone call.
    """

    HOSTED_CHAT = "hosted_chat"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    MESSENGER = "messenger"
    INSTAGRAM = "instagram"
    PHONE = "phone"


class ShareLinkGap(StrEnum):
    """
    Why a channel that is switched on has no link yet: it was connected
    before the platform learned its public address (reconnect it once), or
    the hosted page has no address because CABINET_BASE_URL is not set.
    """

    RECONNECT_CHANNEL = "reconnect_channel"
    NOT_CONFIGURED = "not_configured"


class PublicSlugRefusalCode(StrEnum):
    """Machine-readable reasons a chat address is refused."""

    # Another business uses this address (or used it: printed QR codes keep
    # leading to the business that had it first).
    TAKEN = "slug_taken"
    # A word the platform keeps for its own pages.
    RESERVED = "slug_reserved"
