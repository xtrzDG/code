"""
A WebP picture without its metadata, rebuilt from its own chunks.

A simple WebP (one VP8 or VP8L chunk) carries no metadata. An extended one
(VP8X first) may carry Exif and XMP chunks: they are dropped and their
flags cleared, with every unknown chunk; the frame, alpha, animation and
colour-profile chunks stay. The RIFF size is written anew; the pixels are
never decoded.
"""

from app.schemas.exceptions.media_errors import MalformedMediaFileError

RIFF_TAG: bytes = b"RIFF"
WEBP_TAG: bytes = b"WEBP"
EXTENDED_HEADER: bytes = b"VP8X"
DRAWING_CHUNKS: frozenset[bytes] = frozenset(
    {b"VP8 ", b"VP8L", b"VP8X", b"ALPH", b"ANIM", b"ANMF", b"ICCP"}
)
FRAME_CHUNKS: frozenset[bytes] = frozenset({b"VP8 ", b"VP8L", b"ANMF"})
EXIF_FLAG: int = 0x08
XMP_FLAG: int = 0x04
FOURCC_BYTES: int = 4
SIZE_BYTES: int = 4
# "WEBP" after RIFF's size: the first four bytes the RIFF size counts.
FORM_BYTES: int = 4
CHUNKS_START: int = 12


def strip_webp_metadata(content: bytes) -> bytes:
    """
    The picture with only the chunks that draw it.

    Raises:
        MalformedMediaFileError: not a RIFF WEBP file, a chunk that runs past
            the RIFF's end, or no image frame.
    """

    if len(content) < CHUNKS_START or not (
        content.startswith(RIFF_TAG) and content[8:CHUNKS_START] == WEBP_TAG
    ):
        raise MalformedMediaFileError("A WebP file is a RIFF file of form WEBP.")

    riff_size: int = int.from_bytes(content[4:8], "little")
    riff_end: int = 8 + riff_size
    if riff_end > len(content) or riff_size < FORM_BYTES:
        raise MalformedMediaFileError("The WebP file is shorter than its RIFF size.")

    chunks: list[bytes] = []
    has_frame: bool = False
    position: int = CHUNKS_START
    while position < riff_end:
        fourcc, chunk, position = read_chunk(content, position, riff_end)
        if fourcc not in DRAWING_CHUNKS:
            continue

        has_frame = has_frame or fourcc in FRAME_CHUNKS
        chunks.append(
            without_metadata_flags(chunk) if fourcc == EXTENDED_HEADER else chunk
        )

    if not has_frame:
        raise MalformedMediaFileError("The WebP file has no image frame.")

    body: bytes = WEBP_TAG + b"".join(chunks)
    return RIFF_TAG + len(body).to_bytes(4, "little") + body


def read_chunk(
    content: bytes, position: int, riff_end: int
) -> tuple[bytes, bytes, int]:
    """A chunk's FourCC, its whole bytes (with padding) and the position after it."""

    header_end: int = position + FOURCC_BYTES + SIZE_BYTES
    if header_end > riff_end:
        raise MalformedMediaFileError("A WebP chunk header is cut off.")

    size: int = int.from_bytes(content[position + FOURCC_BYTES : header_end], "little")
    end: int = header_end + size + (size % 2)
    if end > riff_end:
        raise MalformedMediaFileError("A WebP chunk runs past the end of the file.")

    return content[position : position + FOURCC_BYTES], content[position:end], end


def without_metadata_flags(chunk: bytes) -> bytes:
    """The VP8X header with its Exif and XMP flags cleared."""

    flags_at: int = FOURCC_BYTES + SIZE_BYTES
    if len(chunk) <= flags_at:
        raise MalformedMediaFileError("The WebP extended header is cut off.")

    flags: int = chunk[flags_at] & ~(EXIF_FLAG | XMP_FLAG)
    return chunk[:flags_at] + bytes((flags,)) + chunk[flags_at + 1 :]
