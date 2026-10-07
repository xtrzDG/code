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


class WidgetTheme(StrEnum):
    """
    The website chat's colours when the script tag asks for them
    (`data-theme`); without it the widget follows the visitor's system.
    """

    LIGHT = "light"
    DARK = "dark"


class WidgetHandoffReason(StrEnum):
    """
    Why a website visitor's conversation goes to staff from the widget:
    the visitor pressed "Talk to a person", or the widget waited for an
    answer that never came (no worker answered in time), so a person
    answers instead of the typing dots just disappearing.
    """

    CUSTOMER_REQUEST = "customer_request"
    NO_ANSWER = "no_answer"


class InboundContextNote(StrEnum):
    """
    What a customer message refers to that the assistant cannot see, as
    the channel told it: a reply to the business's Instagram story, or a
    mention of the business in the customer's own story.
    """

    STORY_REPLY = "story_reply"
    STORY_MENTION = "story_mention"
