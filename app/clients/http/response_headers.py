"""Reading the few response headers the safe fetcher needs."""

from pydantic import ValidationError

from app.schemas.typings.web_fetching.constrained_strings import (
    WebCharsetName,
    WebMediaType,
)

# A response without a Content-Type is read as a web page.
DEFAULT_MEDIA_TYPE: str = "text/html"
UNKNOWN_MEDIA_TYPE: str = "application/octet-stream"


def header_value(headers: list[tuple[bytes, bytes]], name: str) -> str | None:
    """The first value of a header (names compared without case)."""

    wanted: bytes = name.lower().encode("ascii")
    for key, value in headers:
        if key.lower() == wanted:
            return value.decode("latin-1")

    return None


def read_media_type(content_type: str | None) -> str:
    """ "text/HTML; charset=UTF-8" -> "text/html"; an odd value is unknown."""

    if content_type is None or content_type.strip() == "":
        return DEFAULT_MEDIA_TYPE

    media_type: str = content_type.split(";", 1)[0].strip().lower()
    try:
        return str(WebMediaType(media_type))
    except ValidationError, ValueError:
        return UNKNOWN_MEDIA_TYPE


def read_charset(content_type: str | None) -> WebCharsetName | None:
    """The charset parameter of a Content-Type, when it is a sensible name."""

    if content_type is None:
        return None

    for parameter in content_type.split(";")[1:]:
        key, _, value = parameter.partition("=")
        if key.strip().lower() != "charset":
            continue

        try:
            return WebCharsetName(value.strip().strip("\"'").lower())
        except ValidationError, ValueError:
            return None

    return None
