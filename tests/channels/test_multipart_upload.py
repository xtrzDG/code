"""The widget upload's multipart body, parsed without a form library."""

import pytest

from app.gateways.http.multipart_upload import parse_file_part
from app.schemas.exceptions.application_errors import ValidationFailedError

BOUNDARY: str = "----widget7MA4YWxkTrZu0gW"
FORM: str = f"multipart/form-data; boundary={BOUNDARY}"


def body(*parts: tuple[str, bytes, str | None]) -> bytes:
    """A multipart body of (field name, content, content type) parts."""

    chunks: list[bytes] = []
    for name, content, content_type in parts:
        headers = f'Content-Disposition: form-data; name="{name}"; filename="x"\r\n'
        if content_type is not None:
            headers += f"Content-Type: {content_type}\r\n"
        chunks.append(
            f"--{BOUNDARY}\r\n".encode()
            + headers.encode()
            + b"\r\n"
            + content
            + b"\r\n"
        )
    return b"".join(chunks) + f"--{BOUNDARY}--\r\n".encode()


def test_the_file_part_comes_with_its_declared_type() -> None:
    content = b"\x89PNG\r\n\x1a\n\r\n--not-the-boundary\r\n" + bytes(range(256))

    part = parse_file_part(body(("file", content, "image/png")), FORM)

    assert part.content == content
    assert part.declared_type == "image/png"


def test_a_quoted_boundary_and_a_missing_type_are_read() -> None:
    quoted = f'multipart/form-data; boundary="{BOUNDARY}"'

    part = parse_file_part(body(("file", b"abc", None)), quoted)

    assert (part.content, part.declared_type) == (b"abc", None)


@pytest.mark.parametrize(
    ("raw", "content_type"),
    [
        (body(("file", b"a", None), ("file", b"b", None)), FORM),
        (body(("photo", b"a", None)), FORM),
        (body(), FORM),
        (body(("file", b"a", None)), "application/json"),
        (body(("file", b"a", None)), "multipart/form-data"),
        (body(("file", b"a", None)), None),
        (body(("file", b"a", None))[:-12], FORM),
        (b"--" + BOUNDARY.encode() + b"\r\nno headers end", FORM),
    ],
)
def test_anything_but_one_file_part_is_refused(
    raw: bytes, content_type: str | None
) -> None:
    with pytest.raises(ValidationFailedError):
        parse_file_part(raw, content_type)
