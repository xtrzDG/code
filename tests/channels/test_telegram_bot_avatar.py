"""A bot's profile photo: which size, and only real images become data URLs."""

import pytest

from app.clients.telegram.telegram_bot_client import choose_avatar_size
from app.schemas.typings.media.strings import ProviderMediaId
from app.use_cases.channels.connection.telegram_avatar import (
    MAX_AVATAR_BYTES,
    as_data_url,
    detect_image_type,
)

PNG: bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
WEBP: bytes = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 16
JPEG: bytes = b"\xff\xd8\xff\xdb" + b"\x00" * 16


@pytest.mark.parametrize(
    ("content", "media_type"),
    [
        (JPEG, "image/jpeg"),
        (PNG, "image/png"),
        (WEBP, "image/webp"),
        (b"RIFF\x24\x00\x00\x00WAVEfmt ", None),
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", None),
        (b"", None),
    ],
)
def test_only_jpeg_png_and_webp_count_as_photos(
    content: bytes, media_type: str | None
) -> None:
    assert detect_image_type(content) == media_type


def test_a_photo_becomes_a_data_url_unless_it_is_too_large() -> None:
    small = as_data_url(PNG)
    too_large = as_data_url(JPEG + b"\x00" * MAX_AVATAR_BYTES)

    assert small is not None
    assert str(small).startswith("data:image/png;base64,iVBORw0KGgo")
    assert too_large is None
    assert as_data_url(b"GIF89a") is None


def test_the_smallest_size_wide_enough_else_the_largest_is_chosen() -> None:
    def size(file_id: str | None, width: int | None) -> dict[str, object]:
        entry: dict[str, object] = {}
        if file_id is not None:
            entry["file_id"] = file_id
        if width is not None:
            entry["width"] = width
        return entry

    wide = [size("big", 640), size("mid", 320), size("small", 160)]
    narrow = [size("a", 40), size("b", 64)]

    assert choose_avatar_size(wide) == ProviderMediaId("small")
    assert choose_avatar_size(narrow) == ProviderMediaId("b")
    assert choose_avatar_size([size("x", None)]) == ProviderMediaId("x")
    assert choose_avatar_size([size(None, 160)]) is None
    assert choose_avatar_size([]) is None
