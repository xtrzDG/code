"""
The widget upload's multipart body, read as it streams without a form
library: the same file comes out whatever the chunks the body arrives in,
and anything but one `file` part is refused.
"""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from tests.channels.multipart_bodies import (
    BOUNDARY,
    FORM,
    multipart_body,
    read_upload,
)

# One byte at a time, odd sizes that split the boundary, the whole body.
CHUNK_SIZES: list[int] = [1, 3, 17, 64, 1000, 1_000_000]


@pytest.mark.parametrize("chunk_size", CHUNK_SIZES)
def test_the_file_part_comes_with_its_declared_type(chunk_size: int) -> None:
    content = (
        b"\x89PNG\r\n\x1a\n\r\n--not-the-boundary\r\n"
        + b"\r\n--"
        + BOUNDARY.encode()[:-1]
        + b"!"
        + bytes(range(256))
    )

    declared, file = read_upload(
        multipart_body(("file", content, "image/png")), chunk_size=chunk_size
    )

    assert file == content
    assert declared == "image/png"


@pytest.mark.parametrize("chunk_size", CHUNK_SIZES)
def test_a_file_ending_like_a_line_break_keeps_its_bytes(chunk_size: int) -> None:
    content = b"abc\r\n\r\n-"

    _, file = read_upload(
        multipart_body(("file", content, None)), chunk_size=chunk_size
    )

    assert file == content


def test_a_quoted_boundary_a_preamble_and_a_missing_type_are_read() -> None:
    quoted = f'multipart/form-data; boundary="{BOUNDARY}"'
    body = b"a preamble the form may have\r\n" + multipart_body(("file", b"abc", None))

    assert read_upload(body, quoted) == (None, b"abc")
    assert read_upload(multipart_body(("file", b"", None))) == (None, b"")


@pytest.mark.parametrize("chunk_size", [1, 1_000_000])
@pytest.mark.parametrize(
    ("raw", "content_type"),
    [
        (multipart_body(("file", b"a", None), ("file", b"b", None)), FORM),
        (multipart_body(("photo", b"a", None)), FORM),
        (multipart_body(("note", b"a", None), ("file", b"b", None)), FORM),
        (multipart_body(), FORM),
        (multipart_body(("file", b"a", None)), "application/json"),
        (multipart_body(("file", b"a", None)), "multipart/form-data"),
        (multipart_body(("file", b"a", None)), None),
        (multipart_body(("file", b"a", None))[:-12], FORM),
        (multipart_body(("file", b"a", None))[:-4], FORM),
        (b"--" + BOUNDARY.encode() + b"\r\nno headers end", FORM),
        (b"", FORM),
    ],
)
def test_anything_but_one_file_part_is_refused(
    raw: bytes, content_type: str | None, chunk_size: int
) -> None:
    with pytest.raises(ValidationFailedError):
        read_upload(raw, content_type, chunk_size=chunk_size)


def test_a_head_longer_than_the_form_needs_is_refused() -> None:
    preamble = bytes(17 * 1024)

    with pytest.raises(ValidationFailedError):
        read_upload(preamble + multipart_body(("file", b"abc", None)))
