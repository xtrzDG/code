"""
A PNG picture without its metadata, rebuilt from its own chunks.

Kept: the chunks that say how to draw it (header, palette, image data,
transparency, colour space and profile, physical size, animation frames).
Dropped: text chunks (tEXt, zTXt, iTXt: software, author, comments,
sometimes a location), Exif (eXIf), the modification time (tIME), any
private or unknown chunk, and whatever follows the image's end. Every kept
chunk's checksum is verified; the pixels are never decoded.
"""

import zlib

from app.schemas.exceptions.media_errors import MalformedMediaFileError

PNG_SIGNATURE: bytes = b"\x89PNG\r\n\x1a\n"
HEADER_CHUNK: bytes = b"IHDR"
END_CHUNK: bytes = b"IEND"
DRAWING_CHUNKS: frozenset[bytes] = frozenset(
    {
        b"IHDR",
        b"PLTE",
        b"IDAT",
        b"IEND",
        b"tRNS",
        b"cHRM",
        b"gAMA",
        b"iCCP",
        b"sBIT",
        b"sRGB",
        b"cICP",
        b"mDCV",
        b"cLLI",
        b"bKGD",
        b"hIST",
        b"pHYs",
        b"sPLT",
        b"acTL",
        b"fcTL",
        b"fdAT",
    }
)
LENGTH_BYTES: int = 4
TYPE_BYTES: int = 4
CHECKSUM_BYTES: int = 4


def strip_png_metadata(content: bytes) -> bytes:
    """
    The picture with only the chunks that draw it.

    Raises:
        MalformedMediaFileError: no signature, no header first, a chunk that runs
            past the end or fails its checksum, or no end chunk.
    """

    if not content.startswith(PNG_SIGNATURE):
        raise MalformedMediaFileError("A PNG file starts with its signature.")

    kept = bytearray(PNG_SIGNATURE)
    position: int = len(PNG_SIGNATURE)
    is_first: bool = True
    while True:
        chunk_type, chunk, position = read_chunk(content, position)
        if is_first and chunk_type != HEADER_CHUNK:
            raise MalformedMediaFileError("A PNG file's first chunk is its header.")

        is_first = False
        if chunk_type in DRAWING_CHUNKS:
            kept += chunk
        if chunk_type == END_CHUNK:
            return bytes(kept)


def read_chunk(content: bytes, position: int) -> tuple[bytes, bytes, int]:
    """A chunk's type, its whole bytes and the position after it."""

    header_end: int = position + LENGTH_BYTES + TYPE_BYTES
    if header_end > len(content):
        raise MalformedMediaFileError("The PNG file ends before its end chunk.")

    length: int = int.from_bytes(content[position : position + LENGTH_BYTES], "big")
    chunk_type: bytes = content[position + LENGTH_BYTES : header_end]
    data_end: int = header_end + length
    end: int = data_end + CHECKSUM_BYTES
    if end > len(content):
        raise MalformedMediaFileError("A PNG chunk runs past the end of the file.")

    checksum: int = int.from_bytes(content[data_end:end], "big")
    if zlib.crc32(content[position + LENGTH_BYTES : data_end]) != checksum:
        raise MalformedMediaFileError("A PNG chunk fails its checksum.")

    return chunk_type, content[position:end], end
