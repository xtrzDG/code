"""Keep abc order."""

from base_typed_string import BaseTypedString


class ChannelExternalId(BaseTypedString):
    """
    Business account inside a channel (concept channels.external_id).

    WhatsApp phone number id, Meta page id, Telegram bot username, voice agent.
    """


class ChannelSecret(BaseTypedString):
    """Plain channel credential (bot token, page token). Never stored or logged."""


class EncryptedChannelSecret(BaseTypedString):
    """Channel credential encrypted with the platform key; the stored form."""


class WebhookVerificationToken(BaseTypedString):
    """Shared secret used to verify incoming webhooks."""


# Keep abc order for all non example types, if possible.
