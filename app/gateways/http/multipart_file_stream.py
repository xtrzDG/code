"""
The one file of a website chat upload, read as its body streams.

`read_head` reads the form up to the file part's headers (at most
MULTIPART_OVERHEAD_BYTES), so the type they declare picks the cap of its
kind before a byte of the file is read. `read_file` then takes the
file's bytes into one buffer and stops as soon as they pass that cap:
besides the file itself only the chunk at hand is held, and a chunk of
any size is searched for the closing boundary where it lies, never
copied whole. The body must arrive within `deadline_seconds` of the
reader's start (a connection that trickles would hold an upload place).
"""

import io
from collections.abc import AsyncIterator
from dataclasses import dataclass

import anyio

from app.gateways.http.multipart_upload import (
    CLOSING_MARK,
    LINE_BREAK,
    MULTIPART_OVERHEAD_BYTES,
    PartHead,
    find_file_part_head,
    invalid_form,
    read_boundary,
)
from app.schemas.constants.media import WidgetUploadRefusal
from app.schemas.typings.media.constrained_integers import MediaByteLimit
from app.utilities.media.upload_refusals import upload_refused


@dataclass(frozen=True)
class BodyPiece:
    """Bytes of the body not read yet: `data` from `start` on."""

    data: bytes
    start: int = 0


class UploadedFileBuffer:
    """The file's bytes as they come, refused once past `most_bytes`."""

    def __init__(self, most_bytes: MediaByteLimit) -> None:
        self._most_bytes: MediaByteLimit = most_bytes
        self._size: int = 0
        self._content: io.BytesIO = io.BytesIO()

    def write(self, data: bytes | memoryview) -> None:
        self._size += len(data)
        if self._size > int(self._most_bytes):
            raise upload_refused(WidgetUploadRefusal.FILE_TOO_LARGE, self._most_bytes)

        self._content.write(data)

    def content(self) -> bytes:
        # CPython hands over the buffer itself here: no second copy.
        return self._content.getvalue()


class MultipartFileStream:
    """
    Reads the one `file` part of a multipart/form-data body from its
    chunks: first its head (`read_head`), then its bytes (`read_file`).

    Raises (from the constructor and both reads):
        ValidationFailedError: not multipart/form-data, no boundary, a part
            that does not parse, or not exactly one part named `file`
            (422); a file over its cap (`file_too_large`); a body that did
            not arrive in time (`upload_too_slow`).
    """

    def __init__(
        self,
        chunks: AsyncIterator[bytes],
        content_type: str | None,
        declared_length: str | None,
        deadline_seconds: float,
    ) -> None:
        self._chunks: AsyncIterator[bytes] = chunks
        self._delimiter: bytes = CLOSING_MARK + read_boundary(content_type)
        self._declared_length: str | None = declared_length
        self._deadline: float = anyio.current_time() + deadline_seconds
        self._unread: list[BodyPiece] = []

    async def read_head(self) -> str | None:
        """The type the file part declares (None: none); its headers are read."""

        head = bytearray()
        while True:
            chunk: bytes | None = await self._receive()
            if chunk is None:
                raise invalid_form()

            taken: bytes = chunk[: MULTIPART_OVERHEAD_BYTES - len(head)]
            head += taken
            found: PartHead | None = find_file_part_head(head, self._delimiter)
            if found is not None:
                declared_type, content_start = found
                self._unread = [
                    BodyPiece(bytes(head[content_start:])),
                    BodyPiece(chunk, len(taken)),
                ]
                return declared_type

            if len(head) >= MULTIPART_OVERHEAD_BYTES:
                raise invalid_form()

    async def read_file(self, most_file_bytes: MediaByteLimit) -> bytes:
        """The file's bytes, up to the closing boundary."""

        declared: str | None = self._declared_length
        if (
            declared is not None
            and declared.isdigit()
            and int(declared) > int(most_file_bytes) + MULTIPART_OVERHEAD_BYTES
        ):
            raise upload_refused(WidgetUploadRefusal.FILE_TOO_LARGE, most_file_bytes)

        terminator: bytes = LINE_BREAK + self._delimiter
        keep: int = len(terminator) - 1
        buffer = UploadedFileBuffer(most_file_bytes)
        carry: bytes = b""
        while True:
            piece: BodyPiece | None = await self._next_piece()
            if piece is None:
                raise invalid_form()

            data, start = piece.data, piece.start
            # The boundary may begin in the carried bytes of the last piece.
            joint: bytes = carry + data[start : start + keep]
            found: int = joint.find(terminator)
            if found >= 0:
                buffer.write(joint[:found])
                after: int = start + found + len(terminator) - len(carry)
                return await self._closed(buffer, BodyPiece(data, after))

            found = data.find(terminator, start)
            if found >= 0:
                buffer.write(carry)
                buffer.write(memoryview(data)[start:found])
                return await self._closed(
                    buffer, BodyPiece(data, found + len(terminator))
                )

            if len(data) - start >= keep:
                buffer.write(carry)
                buffer.write(memoryview(data)[start : len(data) - keep])
                carry = data[len(data) - keep :]
            else:
                joined: bytes = carry + data[start:]
                cut: int = max(0, len(joined) - keep)
                buffer.write(joined[:cut])
                carry = joined[cut:]

    async def _closed(self, buffer: UploadedFileBuffer, rest: BodyPiece) -> bytes:
        """The file, when the boundary after it closes the form (no 2nd part)."""

        tail: bytes = rest.data[rest.start : rest.start + len(CLOSING_MARK)]
        while len(tail) < len(CLOSING_MARK):
            piece: BodyPiece | None = await self._next_piece()
            if piece is None:
                raise invalid_form()

            missing: int = len(CLOSING_MARK) - len(tail)
            tail += piece.data[piece.start : piece.start + missing]

        if tail != CLOSING_MARK:
            raise invalid_form()

        return buffer.content()

    async def _next_piece(self) -> BodyPiece | None:
        if self._unread:
            return self._unread.pop(0)

        chunk: bytes | None = await self._receive()
        return None if chunk is None else BodyPiece(chunk)

    async def _receive(self) -> bytes | None:
        """The next chunk of the body (None at its end), within the deadline."""

        remaining: float = max(0.0, self._deadline - anyio.current_time())
        try:
            with anyio.fail_after(remaining):
                return await anext(self._chunks, None)
        except TimeoutError as error:
            raise upload_refused(WidgetUploadRefusal.UPLOAD_TOO_SLOW) from error
