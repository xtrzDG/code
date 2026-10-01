"""Keep abc order."""

from base_typed_string import BaseTypedString


class ChannelAccountId(BaseTypedString):
    """
    Business account inside a channel.

    WhatsApp phone number id, Meta page id, Telegram bot username, etc.
    """


class ChannelSecret(BaseTypedString):
    """Credential of a channel account (bot token, access token). Never logged."""


class WebhookVerificationToken(BaseTypedString):
    """Shared secret used to verify incoming channel webhooks."""


# Keep abc order for all non example types, if possible.
