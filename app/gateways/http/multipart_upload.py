"""
One file of a multipart/form-data request body, read at the transport
boundary without a form library.

The widget's upload sends one part named `file` (the browser's FormData).
The body is read up to a cap the use case allows (no more is ever held),
then split at its boundary; anything but exactly one `file` part is
refused. The part's declared Content-Type travels on as the browser's
claim, which the use case checks against the file's own bytes.
"""

import re
from dataclasses import dataclass

from fastapi import Request

from app.schemas.constants.media import WidgetUploadRefusal
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.media.upload_refusals import upload_refused

FILE_FIELD_NAME: str = "file"
# Room for the boundaries and the part's headers around the file itself.
MULTIPART_OVERHEAD_BYTES: int = 16 * 1024
BOUNDARY_PATTERN: re.Pattern[str] = re.compile(
    r"""boundary=(?:"([^"]{1,70})"|([^\s;"]{1,70}))""", re.IGNORECASE
)
NAME_PATTERN: re.Pattern[str] = re.compile(r"""(?:^|;)\s*name="([^"]*)\"""")
MULTIPART_TYPE: str = "multipart/form-data"
LINE_BREAK: bytes = b"\r\n"
HEADERS_END: bytes = b"\r\n\r\n"
CLOSING_MARK: bytes = b"--"
INVALID_FORM: str = (
    "The upload must be a multipart/form-data body with one part named file."
)


@dataclass(frozen=True)
class UploadedFilePart:
    """The file part of an upload: its bytes and the type its sender declared."""

    content: bytes
    declared_type: str | None


async def read_limited_body(request: Request, most_file_bytes: int) -> bytes:
    """
    The body, read as it streams, refused (422 `file_too_large`) as soon as
    it is longer than the file allowed plus the form around it.
    """

    limit: int = most_file_bytes + MULTIPART_OVERHEAD_BYTES
    declared_length: str | None = request.headers.get("content-length")
    is_declared_too_long: bool = (
        declared_length is not None
        and declared_length.isdigit()
        and int(declared_length) > limit
    )
    if is_declared_too_long:
        raise upload_refused(WidgetUploadRefusal.FILE_TOO_LARGE, most_file_bytes)

    received = bytearray()
    async for chunk in request.stream():
        received += chunk
        if len(received) > limit:
            raise upload_refused(WidgetUploadRefusal.FILE_TOO_LARGE, most_file_bytes)

    return bytes(received)


def parse_file_part(body: bytes, content_type: str | None) -> UploadedFilePart:
    """
    The one part named `file` of a multipart/form-data body.

    Raises:
        ValidationFailedError: not multipart/form-data, no boundary, a part
            that does not parse, or not exactly one `file` part.
    """

    boundary: bytes = read_boundary(content_type)
    files: list[UploadedFilePart] = []
    for part in split_parts(body, CLOSING_MARK + boundary):
        headers, separator, content = part.partition(HEADERS_END)
        if not separator:
            raise ValidationFailedError(INVALID_FORM)

        fields: dict[str, str] = read_part_headers(headers)
        name: re.Match[str] | None = NAME_PATTERN.search(
            fields.get("content-disposition", "")
        )
        if name is None or name.group(1) != FILE_FIELD_NAME:
            raise ValidationFailedError(INVALID_FORM)

        files.append(UploadedFilePart(content, fields.get("content-type")))

    if len(files) != 1:
        raise ValidationFailedError(INVALID_FORM)

    return files[0]


def read_boundary(content_type: str | None) -> bytes:
    if content_type is None or not content_type.lower().startswith(MULTIPART_TYPE):
        raise ValidationFailedError(INVALID_FORM)

    found: re.Match[str] | None = BOUNDARY_PATTERN.search(content_type)
    if found is None:
        raise ValidationFailedError(INVALID_FORM)

    return (found.group(1) or found.group(2)).encode("latin-1")


def split_parts(body: bytes, delimiter: bytes) -> list[bytes]:
    """The parts between the delimiters (the preamble and epilogue left out)."""

    start: int = body.find(delimiter)
    if start < 0:
        raise ValidationFailedError(INVALID_FORM)

    parts: list[bytes] = []
    position: int = start + len(delimiter)
    while not body.startswith(CLOSING_MARK, position):
        if not body.startswith(LINE_BREAK, position):
            raise ValidationFailedError(INVALID_FORM)

        position += len(LINE_BREAK)
        end: int = body.find(LINE_BREAK + delimiter, position)
        if end < 0:
            raise ValidationFailedError(INVALID_FORM)

        parts.append(body[position:end])
        position = end + len(LINE_BREAK) + len(delimiter)

    return parts


def read_part_headers(headers: bytes) -> dict[str, str]:
    """A part's headers by lower-case name (values as sent, latin-1)."""

    fields: dict[str, str] = {}
    for line in headers.decode("latin-1").split("\r\n"):
        name, separator, value = line.partition(":")
        if separator:
            fields[name.strip().lower()] = value.strip()

    return fields
