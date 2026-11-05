"""
The upload body is read as it streams and never held more than once: the
reading stops as soon as the file passes the cap it was given (or before
it starts, when the declared length is already over), the file is kept in
one buffer however the body is chunked, and a body that trickles is
refused once its time is up. Before, the whole body was buffered, copied
to bytes and sliced again: three copies of a 16 MiB file at once.
"""

import asyncio
import tracemalloc
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.gateways.http.multipart_file_stream import MultipartFileStream
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.media.constrained_integers import MediaByteLimit
from tests.channels.multipart_bodies import FORM, part_head

CHUNK: int = 64 * 1024
FILE_BYTES: int = 8 * 1024 * 1024
CLOSING: bytes = b"\r\n--" + FORM.split("boundary=")[1].encode() + b"--\r\n"


class CountingBody:
    """A body of a head and then `file_bytes` zeros, counting what was read."""

    def __init__(self, head: bytes, file_bytes: int, chunk: int = CHUNK) -> None:
        self.head: bytes = head
        self.file_bytes: int = file_bytes
        self.chunk: int = chunk
        self.file_bytes_read: int = 0

    async def chunks(self) -> AsyncIterator[bytes]:
        yield self.head
        sent = 0
        while sent < self.file_bytes:
            size = min(self.chunk, self.file_bytes - sent)
            sent += size
            self.file_bytes_read = sent
            yield bytes(size)
        yield CLOSING


def refusal_code(error: ValidationFailedError) -> str:
    return str(error.reasons[0].code)


async def read(
    chunks: AsyncIterator[bytes],
    most_bytes: int,
    declared_length: str | None = None,
    deadline_seconds: float = 60.0,
) -> bytes:
    stream = MultipartFileStream(chunks, FORM, declared_length, deadline_seconds)
    await stream.read_head()
    return await stream.read_file(MediaByteLimit(most_bytes))


class TestCap:
    def test_reading_stops_once_the_file_passes_its_cap(self) -> None:
        # A photo's cap of 64 KiB on a body that would carry 16 MiB.
        body = CountingBody(part_head(content_type="image/jpeg"), 16 * 1024 * 1024)

        with pytest.raises(ValidationFailedError) as refused:
            asyncio.run(read(body.chunks(), 64 * 1024))

        assert refusal_code(refused.value) == "file_too_large"
        assert body.file_bytes_read <= 64 * 1024 + 2 * CHUNK

    def test_a_declared_length_over_the_cap_is_refused_before_the_file(
        self,
    ) -> None:
        body = CountingBody(part_head(content_type="image/jpeg"), 4 * CHUNK)

        with pytest.raises(ValidationFailedError) as refused:
            asyncio.run(read(body.chunks(), CHUNK, declared_length=str(4 * CHUNK)))

        assert refusal_code(refused.value) == "file_too_large"
        assert body.file_bytes_read == 0

    def test_a_file_of_exactly_its_cap_is_taken(self) -> None:
        body = CountingBody(part_head(content_type="audio/webm"), 3 * CHUNK + 5)

        content = asyncio.run(read(body.chunks(), 3 * CHUNK + 5))

        assert content == bytes(3 * CHUNK + 5)


class TestMemory:
    @pytest.mark.parametrize("chunk", [CHUNK, FILE_BYTES])
    def test_the_file_is_held_once_while_it_is_read(self, chunk: int) -> None:
        # Small chunks as a server reads them, or the whole body at once.
        body = CountingBody(part_head(content_type="audio/webm"), FILE_BYTES, chunk)
        held: list[Any] = []

        async def run() -> int:
            tracemalloc.start()
            try:
                content = await read(body.chunks(), 16 * 1024 * 1024)
                held.append(content)
                return tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()

        peak = asyncio.run(run())

        assert len(held[0]) == FILE_BYTES
        # The file once (its buffer grows by an eighth) and the chunk at hand;
        # the earlier reading held it three times (some 24 MiB here).
        assert peak < 1.5 * FILE_BYTES + chunk


class TestDeadline:
    def test_a_body_that_stops_arriving_is_refused_in_time(self) -> None:
        async def trickle() -> AsyncIterator[bytes]:
            yield part_head(content_type="audio/webm")
            yield b"some audio"
            await asyncio.Event().wait()
            yield b"never"

        with pytest.raises(ValidationFailedError) as refused:
            asyncio.run(read(trickle(), CHUNK, deadline_seconds=0.05))

        assert refusal_code(refused.value) == "upload_too_slow"

    def test_a_head_that_never_comes_is_refused_in_time(self) -> None:
        async def silent() -> AsyncIterator[bytes]:
            await asyncio.Event().wait()
            yield b"never"

        with pytest.raises(ValidationFailedError) as refused:
            asyncio.run(read(silent(), CHUNK, deadline_seconds=0.05))

        assert refusal_code(refused.value) == "upload_too_slow"
