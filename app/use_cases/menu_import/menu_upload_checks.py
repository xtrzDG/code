"""
What an uploaded menu file really is (ASVS V5.2.2): its declared type must
match its first bytes, so an HTML page renamed to menu.pdf or menu.png is
refused before a model reads it.

Photos are read by their signature, a PDF must start with `%PDF-`, and a
text or CSV file must be UTF-8 without NUL bytes and must not be markup
(an HTML or SVG document saved as .txt). HTML files are not uploads at all:
a web page is imported by its link, where the served type is checked.
"""

import base64
import binascii

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.menu_import.constrained_strings import (
    MenuSourceBase64,
    MenuSourceMediaType,
)
from app.utilities.media.media_sniffing import sniff_image

IMAGE_UPLOAD_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)
PDF_UPLOAD_TYPE: str = "application/pdf"
TEXT_UPLOAD_TYPES: frozenset[str] = frozenset({"text/plain", "text/csv"})
UPLOAD_MEDIA_TYPES: frozenset[str] = (
    IMAGE_UPLOAD_TYPES | {PDF_UPLOAD_TYPE} | TEXT_UPLOAD_TYPES
)
PDF_SIGNATURE: bytes = b"%PDF-"
UTF8_BOM: bytes = b"\xef\xbb\xbf"
# A text file that opens with one of these is a markup document.
MARKUP_OPENINGS: tuple[bytes, ...] = (
    b"<!doctype",
    b"<html",
    b"<head",
    b"<body",
    b"<script",
    b"<svg",
    b"<?xml",
    b"<iframe",
)
# Base64 characters decoded to read a file's signature (48 bytes).
SIGNATURE_CHARACTERS: int = 64
SIGNATURE_BYTES: int = 12
UNSUPPORTED_TYPE_TEXT: str = (
    "A menu file must be a JPEG, PNG, WebP or GIF photo, a PDF or text."
)
MISMATCH_TEXT: str = "The menu file's content does not match its type."


def check_menu_upload(
    media_type: MenuSourceMediaType, data_base64: MenuSourceBase64
) -> None:
    """Raise ValidationFailedError unless the file is what it says it is."""

    declared: str = str(media_type)
    if declared not in UPLOAD_MEDIA_TYPES:
        raise ValidationFailedError(UNSUPPORTED_TYPE_TEXT)

    if declared in TEXT_UPLOAD_TYPES:
        check_text(decode(str(data_base64)))
        return

    head: bytes = decode(str(data_base64)[:SIGNATURE_CHARACTERS])
    if declared == PDF_UPLOAD_TYPE:
        if not head.startswith(PDF_SIGNATURE):
            raise ValidationFailedError(MISMATCH_TEXT)

        return

    if sniff_image(head) != declared:
        raise ValidationFailedError(MISMATCH_TEXT)


def check_text(content: bytes) -> None:
    is_binary: bool = (
        b"\x00" in content
        or content.startswith(PDF_SIGNATURE)
        or sniff_image(content[:SIGNATURE_BYTES]) is not None
    )
    if is_binary:
        raise ValidationFailedError(MISMATCH_TEXT)

    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationFailedError(
            "A menu text file must be saved as UTF-8."
        ) from None

    opening: bytes = content.removeprefix(UTF8_BOM).lstrip()[:16].lower()
    if opening.startswith(MARKUP_OPENINGS):
        raise ValidationFailedError(MISMATCH_TEXT)


def decode(data_base64: str) -> bytes:
    try:
        return base64.b64decode(data_base64, validate=True)
    except binascii.Error, ValueError:
        raise ValidationFailedError("The menu file is not valid base64.") from None
