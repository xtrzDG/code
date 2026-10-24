"""The addresses customer files are downloaded from: Meta's own hosts only."""

from urllib.parse import urlsplit

from app.schemas.exceptions.media_errors import MediaUnavailableError
from app.schemas.typings.media.strings import MediaDownloadUrl

# Meta's media and CDN hosts (WhatsApp media URLs, Messenger and Instagram
# attachment URLs).
META_MEDIA_HOST_SUFFIXES: tuple[str, ...] = (
    ".fbcdn.net",
    ".fbsbx.com",
    ".cdninstagram.com",
    ".facebook.com",
    ".whatsapp.net",
)


def require_meta_media_url(raw_url: str) -> MediaDownloadUrl:
    """
    An https URL on a Meta host, without credentials in it; anything else
    raises MediaUnavailableError (it is never fetched).
    """

    try:
        parts = urlsplit(raw_url)
    except ValueError as error:
        raise MediaUnavailableError("The attachment address is malformed.") from error

    host: str = (parts.hostname or "").lower()
    if (
        parts.scheme != "https"
        or parts.username is not None
        or parts.password is not None
        or not any(host.endswith(suffix) for suffix in META_MEDIA_HOST_SUFFIXES)
    ):
        raise MediaUnavailableError("The attachment is not on a Meta media host.")

    return MediaDownloadUrl(raw_url)
