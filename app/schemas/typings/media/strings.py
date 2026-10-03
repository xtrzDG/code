"""Keep abc order."""

from base_typed_string import BaseTypedString


class AttachmentCaption(BaseTypedString):
    """Text a customer wrote under a photo, a voice note or a file."""


class LocationAddress(BaseTypedString):
    """Street address the messenger attached to a shared location."""


class LocationName(BaseTypedString):
    """Name of a place the customer shared (a venue, a landmark)."""


class MapLinkUrl(BaseTypedString):
    """Link that opens a shared place on a map, e.g. "https://maps.google.com/?q=41.7,44.8"."""


class MediaDownloadUrl(BaseTypedString):
    """
    Address a platform hands out for downloading one customer file (a
    WhatsApp media URL, valid for minutes; a Meta CDN attachment URL).
    """


class MediaStoragePath(BaseTypedString):
    """Path of a stored customer file in the platform's media storage."""


class ProviderMediaId(BaseTypedString):
    """
    The messaging platform's reference to a file a customer sent: a WhatsApp
    media id, a Telegram file_id, or the attachment URL of Messenger and
    Instagram.
    """


class ProviderMediaType(BaseTypedString):
    """
    Media type the platform declared for a file, as it sent it (it may carry
    parameters: "audio/ogg; codecs=opus"). Never trusted for storage: the
    stored type comes from the file's own bytes.
    """


class TelegramFilePath(BaseTypedString):
    """Path of a file on Telegram's servers, as getFile returns it."""


class TranscribedVoiceText(BaseTypedString):
    """What a customer said in a voice note, as the transcription heard it."""


# Keep abc order for all non example types, if possible.
