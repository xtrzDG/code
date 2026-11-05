"""
Multipart bodies as the widget's FormData sends them, and the upload
reader driven over them in chunks of a chosen size.
"""

import asyncio
from collections.abc import AsyncIterator

from app.gateways.http.multipart_file_stream import MultipartFileStream
from app.schemas.typings.media.constrained_integers import MediaByteLimit

BOUNDARY: str = "----widget7MA4YWxkTrZu0gW"
FORM: str = f"multipart/form-data; boundary={BOUNDARY}"
MOST_BYTES: int = 1_000_000


def multipart_body(*parts: tuple[str, bytes, str | None]) -> bytes:
    """A multipart body of (field name, content, content type) parts."""

    chunks: list[bytes] = []
    for name, content, content_type in parts:
        chunks.append(part_head(name, content_type) + content + b"\r\n")
    return b"".join(chunks) + f"--{BOUNDARY}--\r\n".encode()


def part_head(name: str = "file", content_type: str | None = None) -> bytes:
    """A part's delimiter and headers, up to where its content starts."""

    headers = f'Content-Disposition: form-data; name="{name}"; filename="x"\r\n'
    if content_type is not None:
        headers += f"Content-Type: {content_type}\r\n"
    return f"--{BOUNDARY}\r\n".encode() + headers.encode() + b"\r\n"


async def chunks_of(body: bytes, size: int) -> AsyncIterator[bytes]:
    for start in range(0, len(body), size):
        yield body[start : start + size]


async def read_upload_async(
    raw: bytes,
    content_type: str | None = FORM,
    chunk_size: int = MOST_BYTES,
    most_bytes: int = MOST_BYTES,
) -> tuple[str | None, bytes]:
    stream = MultipartFileStream(chunks_of(raw, chunk_size), content_type, None, 60.0)
    declared: str | None = await stream.read_head()
    return declared, await stream.read_file(MediaByteLimit(most_bytes))


def read_upload(
    raw: bytes,
    content_type: str | None = FORM,
    chunk_size: int = MOST_BYTES,
    most_bytes: int = MOST_BYTES,
) -> tuple[str | None, bytes]:
    """The declared type and the file of `raw`, read in `chunk_size` chunks."""

    return asyncio.run(read_upload_async(raw, content_type, chunk_size, most_bytes))
