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


class ManagerLinkCodeHash(BaseTypedString):
    """SHA-256 hex digest of a manager link code; codes are never stored."""


class MetaPageName(BaseTypedString):
    """Name of a Facebook page as Meta reports it."""


class MetaWebhookChallenge(BaseTypedString):
    """Random value Meta sends to verify a webhook; echoed back verbatim."""


class MetaWebhookMode(BaseTypedString):
    """`hub.mode` of a Meta webhook verification request ("subscribe")."""


class OutboundMessagePart(BaseTypedString):
    """
    Text of one platform message sent to a person: a reply or notification,
    or one part of it when it is longer than the channel allows.
    """


class PresentedWebhookSecret(BaseTypedString):
    """Shared secret a caller presents in a header; compared in constant time."""


class ProviderMessageId(BaseTypedString):
    """
    Id of a message inside a messaging platform.

    WhatsApp "wamid...", Messenger and Instagram "mid...", Telegram
    "<chat id>:<message id>".
    """


class RawChannelSecretInput(BaseTypedString):
    """
    Bot or page token as the owner pasted it, before it is checked.

    Becomes a ChannelSecret once its shape is validated.
    """


class VoicePlatformToolId(BaseTypedString):
    """Id of a webhook tool registered on the voice platform."""


class WebhookSignatureHeader(BaseTypedString):
    """
    Raw signature header of a webhook delivery, before it is checked.

    Examples: "sha256=<hex>" (Meta), "t=<unix>,v0=<hex>" (ElevenLabs).
    """


class WebhookVerificationToken(BaseTypedString):
    """Shared secret used to verify incoming webhooks."""


class WhatsAppDisplayPhoneNumber(BaseTypedString):
    """Phone number of a WhatsApp business account as Meta displays it."""


class WidgetContactNameInput(BaseTypedString):
    """Name a visitor typed into the website widget, before it is checked."""


class WidgetEmbedSnippet(BaseTypedString):
    """HTML snippet the owner pastes into the website to show the chat widget."""


# Keep abc order for all non example types, if possible.
