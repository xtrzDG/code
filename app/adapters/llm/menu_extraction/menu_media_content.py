"""Responses input parts for a menu photo, PDF, text or web page."""

import base64
import binascii

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.knowledge.website.html_to_text import html_to_text

IMAGE_MEDIA_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)
PDF_MEDIA_TYPE: str = "application/pdf"
TEXT_MEDIA_TYPES: frozenset[str] = frozenset({"text/plain", "text/csv", "text/html"})
SUPPORTED_MEDIA_TYPES: frozenset[str] = (
    IMAGE_MEDIA_TYPES | {PDF_MEDIA_TYPE} | TEXT_MEDIA_TYPES
)
HTML_MEDIA_TYPE: str = "text/html"
MAX_MENU_TEXT_CHARACTERS: int = 60_000


def build_media_content(media_type: str, data: bytes) -> list[dict[str, object]]:
    """Responses input parts for a menu file of the given media type."""

    if media_type in IMAGE_MEDIA_TYPES:
        encoded: str = base64.b64encode(data).decode("ascii")
        return [
            {
                "type": "input_image",
                "image_url": f"data:{media_type};base64,{encoded}",
                "detail": "high",
            }
        ]

    if media_type == PDF_MEDIA_TYPE:
        encoded = base64.b64encode(data).decode("ascii")
        return [
            {
                "type": "input_file",
                "filename": "menu.pdf",
                "file_data": f"data:{PDF_MEDIA_TYPE};base64,{encoded}",
            }
        ]

    if media_type in TEXT_MEDIA_TYPES:
        text: str = data.decode("utf-8", errors="replace")
        if media_type == HTML_MEDIA_TYPE:
            text = html_to_text(text, "", MAX_MENU_TEXT_CHARACTERS).text

        return [{"type": "input_text", "text": text[:MAX_MENU_TEXT_CHARACTERS]}]

    raise ValidationFailedError(
        f"Menus can be photos, PDF files, text or web pages, not {media_type}."
    )


def decode_base64(data_base64: str) -> bytes:
    try:
        return base64.b64decode(data_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValidationFailedError("The menu file is not valid base64.") from error
