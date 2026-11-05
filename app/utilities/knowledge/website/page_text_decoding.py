"""
Bytes of a fetched page to text: the charset the server named, else a
byte order mark, else the page's own <meta charset>, else UTF-8.
Undecodable bytes become U+FFFD instead of failing the page.
"""

import codecs
import re

META_CHARSET: re.Pattern[bytes] = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9._:\-]{1,40})""",
    re.IGNORECASE,
)
SNIFF_BYTES: int = 4096
BYTE_ORDER_MARKS: tuple[tuple[bytes, str], ...] = (
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)
FALLBACK_ENCODING: str = "utf-8"


def decode_page(body: bytes, declared_charset: str | None) -> str:
    """The page's text in the best known encoding."""

    return body.decode(choose_encoding(body, declared_charset), errors="replace")


def choose_encoding(body: bytes, declared_charset: str | None) -> str:
    for mark, encoding in BYTE_ORDER_MARKS:
        if body.startswith(mark):
            return encoding

    for candidate in (declared_charset, sniff_meta_charset(body)):
        known: str | None = known_encoding(candidate)
        if known is not None:
            return known

    return FALLBACK_ENCODING


def sniff_meta_charset(body: bytes) -> str | None:
    match: re.Match[bytes] | None = META_CHARSET.search(body[:SNIFF_BYTES])
    return None if match is None else match.group(1).decode("ascii")


def known_encoding(name: str | None) -> str | None:
    """The codec's name when Python knows it (and it is not a binary codec)."""

    if name is None:
        return None

    try:
        info: codecs.CodecInfo = codecs.lookup(name)
    except LookupError:
        return None

    return info.name if getattr(info, "_is_text_encoding", True) else None
