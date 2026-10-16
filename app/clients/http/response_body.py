"""
Reading a response body within the fetch's byte and time limits.

The fetcher asks for an uncompressed body, but a server may compress it
anyway: gzip and deflate are unpacked here, and the limit counts the
unpacked bytes (a few kilobytes cannot unpack into gigabytes).
"""

import zlib
from collections.abc import Callable, Iterable

from app.clients.http.fetch_errors import fetch_error
from app.schemas.constants.web_fetching import WebFetchProblem

IDENTITY_ENCODINGS: frozenset[str] = frozenset({"", "identity"})
ZLIB_ENCODINGS: frozenset[str] = frozenset({"gzip", "x-gzip", "deflate"})
# zlib or gzip framing, recognized from the header.
AUTO_DETECT_WBITS: int = 32 + zlib.MAX_WBITS


def read_limited_body(
    chunks: Iterable[bytes],
    content_encoding: str | None,
    max_bytes: int,
    is_past_deadline: Callable[[], bool],
) -> bytes:
    """
    The whole body, unpacked.

    Raises:
        WebFetchError: TOO_LARGE, TIMEOUT or UNSUPPORTED_ENCODING.
    """

    encoding: str = (content_encoding or "").strip().lower()
    if encoding in IDENTITY_ENCODINGS:
        return read_plain(chunks, max_bytes, is_past_deadline)

    if encoding in ZLIB_ENCODINGS:
        return read_compressed(chunks, max_bytes, is_past_deadline)

    raise fetch_error(
        WebFetchProblem.UNSUPPORTED_ENCODING,
        "The server sent the page in an encoding that cannot be read.",
        encoding,
    )


def read_plain(
    chunks: Iterable[bytes],
    max_bytes: int,
    is_past_deadline: Callable[[], bool],
) -> bytes:
    body = bytearray()
    for chunk in chunks:
        check_deadline(is_past_deadline)
        body.extend(chunk)
        if len(body) > max_bytes:
            raise too_large(max_bytes)

    return bytes(body)


def read_compressed(
    chunks: Iterable[bytes],
    max_bytes: int,
    is_past_deadline: Callable[[], bool],
) -> bytes:
    decompressor = zlib.decompressobj(AUTO_DETECT_WBITS)
    body = bytearray()
    try:
        for chunk in chunks:
            check_deadline(is_past_deadline)
            # One byte more than allowed is enough to know it is too large.
            body.extend(decompressor.decompress(chunk, max_bytes - len(body) + 1))
            if len(body) > max_bytes or decompressor.unconsumed_tail:
                raise too_large(max_bytes)

        body.extend(decompressor.flush())
    except zlib.error as error:
        raise fetch_error(
            WebFetchProblem.UNSUPPORTED_ENCODING,
            "The server sent a damaged compressed page.",
            "corrupt",
        ) from error

    if len(body) > max_bytes:
        raise too_large(max_bytes)

    return bytes(body)


def check_deadline(is_past_deadline: Callable[[], bool]) -> None:
    if is_past_deadline():
        raise fetch_error(WebFetchProblem.TIMEOUT, "The address took too long to read.")


def too_large(max_bytes: int) -> Exception:
    megabytes: float = max_bytes / (1024 * 1024)
    return fetch_error(
        WebFetchProblem.TOO_LARGE,
        f"The page is larger than {megabytes:g} MB.",
    )
