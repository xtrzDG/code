"""
docs/security/upload-limits.md states the limits the code enforces: each
number on the page is checked against the constant it names, and every
code path the page cites exists.
"""

import re
from pathlib import Path

from app.adapters.llm.menu_extraction.menu_link_reading import MAX_MENU_LINK_BYTES
from app.adapters.llm.menu_extraction.menu_media_content import (
    MAX_MENU_TEXT_CHARACTERS,
)
from app.gateways.http.middleware.body_size_limit_middleware import (
    MENU_IMPORT_BODY_LIMIT_BYTES,
    WIDGET_UPLOAD_BODY_LIMIT_BYTES,
)
from app.schemas.configurations.media_settings import (
    DEFAULT_MAX_IMAGE_BYTES,
    DEFAULT_MAX_VOICE_BYTES,
    DEFAULT_MAX_VOICE_SECONDS,
)
from app.schemas.dto.channels.widget import MAX_MESSAGE_ATTACHMENTS
from app.schemas.dto.web_fetching import DEFAULT_WEB_FETCH_BYTES
from app.schemas.typings.menu_import.constrained_strings import MenuSourceBase64
from app.use_cases.channels.connection.telegram_avatar import MAX_AVATAR_BYTES
from app.use_cases.knowledge.website_import.website_page_fetching import MAX_PAGES
from app.use_cases.menu_import.menu_upload_checks import UPLOAD_MEDIA_TYPES
from app.utilities.calendar_sync.feed_addresses import ICAL_FEED_BYTE_LIMIT
from app.utilities.knowledge.website.web_page_reading import MAX_PAGE_CHARACTERS

ROOT: Path = Path(__file__).resolve().parents[2]
PAGE: str = (ROOT / "docs/security/upload-limits.md").read_text(encoding="utf-8")
MEBIBYTE: int = 1024 * 1024


def mib(value: int) -> str:
    return f"{value // MEBIBYTE} MiB"


def test_the_page_states_the_limits_of_the_code() -> None:
    expected: list[str] = [
        f"(default {mib(DEFAULT_MAX_IMAGE_BYTES)})",
        f"(default {mib(DEFAULT_MAX_VOICE_BYTES)})",
        f"(default {DEFAULT_MAX_VOICE_SECONDS} s)",
        f"request body {mib(WIDGET_UPLOAD_BODY_LIMIT_BYTES)}",
        f"{MAX_MESSAGE_ATTACHMENTS} files per message",
        f"({mib(MenuSourceBase64.max_length or 0)} of base64)",
        f"request body {mib(MENU_IMPORT_BODY_LIMIT_BYTES)}",
        f"{MAX_MENU_TEXT_CHARACTERS:,} characters",
        f"{mib(int(MAX_MENU_LINK_BYTES))} after decompression",
        f"{MAX_PAGES} pages, {mib(int(DEFAULT_WEB_FETCH_BYTES))} each",
        f"{MAX_PAGE_CHARACTERS:,} characters read per page",
        f"{mib(int(ICAL_FEED_BYTE_LIMIT))} after decompression",
        f"{MAX_AVATAR_BYTES // 1024} KiB",
    ]

    assert [text for text in expected if text not in PAGE] == []


def test_html_and_svg_are_no_menu_upload_types() -> None:
    assert {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/pdf",
        "text/plain",
        "text/csv",
    } == UPLOAD_MEDIA_TYPES
    assert "never HTML or SVG" in PAGE


def test_every_cited_code_path_exists() -> None:
    cited: set[str] = set(re.findall(r"`(app/[\w/]+\.py)`", PAGE))

    assert cited
    assert sorted(path for path in cited if not (ROOT / path).is_file()) == []
