"""
The form around the one file of a website chat upload, read at the
transport boundary without a form library.

The widget's upload is multipart/form-data with one part named `file`
(the browser's FormData). These helpers read its boundary and the file
part's headers, whose Content-Type travels on as the browser's claim
(the use cases check it against the file's own bytes); anything but one
`file` part is refused. `multipart_file_stream` reads the body with them
as it streams.
"""

import re

from app.schemas.exceptions.application_errors import ValidationFailedError

FILE_FIELD_NAME: str = "file"
# Room for the preamble, the boundaries and the part's headers.
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

type PartHead = tuple[str | None, int]


def invalid_form() -> ValidationFailedError:
    return ValidationFailedError(INVALID_FORM)


def read_boundary(content_type: str | None) -> bytes:
    """
    The boundary of a multipart/form-data body.

    Raises:
        ValidationFailedError: another type, or no boundary.
    """

    if content_type is None or not content_type.lower().startswith(MULTIPART_TYPE):
        raise invalid_form()

    found: re.Match[str] | None = BOUNDARY_PATTERN.search(content_type)
    if found is None:
        raise invalid_form()

    return (found.group(1) or found.group(2)).encode("latin-1")


def find_file_part_head(head: bytearray, delimiter: bytes) -> PartHead | None:
    """
    The type the first part declares and where its content starts, once
    `head` (the body's first bytes) holds the first delimiter and the
    part's headers; None while it does not yet.

    Raises:
        ValidationFailedError: a body without parts, or a first part that
            is not the one named `file`.
    """

    start: int = head.find(delimiter)
    if start < 0:
        return None

    after: int = start + len(delimiter)
    if len(head) < after + len(LINE_BREAK):
        return None

    if not head.startswith(LINE_BREAK, after):
        # The closing delimiter straight away: a form without parts.
        raise invalid_form()

    headers_end: int = head.find(HEADERS_END, after)
    if headers_end < 0:
        return None

    fields: dict[str, str] = read_part_headers(
        bytes(head[after + len(LINE_BREAK) : headers_end])
    )
    name: re.Match[str] | None = NAME_PATTERN.search(
        fields.get("content-disposition", "")
    )
    if name is None or name.group(1) != FILE_FIELD_NAME:
        raise invalid_form()

    return fields.get("content-type"), headers_end + len(HEADERS_END)


def read_part_headers(headers: bytes) -> dict[str, str]:
    """A part's headers by lower-case name (values as sent, latin-1)."""

    fields: dict[str, str] = {}
    for line in headers.decode("latin-1").split("\r\n"):
        name, separator, value = line.partition(":")
        if separator:
            fields[name.strip().lower()] = value.strip()

    return fields
