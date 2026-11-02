"""
A provider's answer read within a byte cap (OWASP API10, ASVS V15.3.2): a
declared Content-Length over the cap is refused before any byte is read,
and the body stops one chunk past the cap. A gzip or deflate answer is
unpacked here, counted after unpacking, so a small compressed answer
cannot grow into gigabytes; any other content coding is refused (the
client asks for gzip only).
"""

import zlib
from collections.abc import Iterator

import httpx

# gzip or zlib, told apart by the header.
AUTO_DETECT_WBITS: int = 32 + zlib.MAX_WBITS
# A raw deflate stream (servers that send "deflate" without the zlib header).
RAW_DEFLATE_WBITS: int = -zlib.MAX_WBITS
UNPACKED_ENCODINGS: frozenset[str] = frozenset({"gzip", "x-gzip", "deflate"})
PLAIN_ENCODINGS: frozenset[str] = frozenset({"", "identity"})


class ProviderResponseTooLargeError(httpx.ReadError):
    """The answer is longer than its client's cap (a transport failure)."""


class ProviderResponseEncodingError(httpx.DecodingError):
    """The answer came in a content coding that is not read, or damaged."""


def cap_response(response: httpx.Response, max_bytes: int) -> None:
    """Make `response` read at most `max_bytes` (unpacked) or raise."""

    declared: str = response.headers.get("content-length", "").strip()
    if declared.isdigit() and int(declared) > max_bytes and not is_encoded(response):
        raise too_large(response.request, max_bytes)

    encoding: str = response.headers.get("content-encoding", "").strip().lower()
    if encoding in PLAIN_ENCODINGS:
        response.stream = CappedStream(response.stream, max_bytes, response.request)
        return

    if encoding not in UNPACKED_ENCODINGS:
        raise ProviderResponseEncodingError(
            f"The provider answered in an unread content coding ({encoding[:20]}).",
            request=response.request,
        )

    # Unpacked here: httpx must not unpack it again.
    del response.headers["content-encoding"]
    if "content-length" in response.headers:
        del response.headers["content-length"]
    response.stream = UnpackingCappedStream(
        response.stream, max_bytes, response.request, encoding
    )


def is_encoded(response: httpx.Response) -> bool:
    encoding: str = response.headers.get("content-encoding", "").strip().lower()
    return encoding not in PLAIN_ENCODINGS


def too_large(request: httpx.Request, max_bytes: int) -> ProviderResponseTooLargeError:
    return ProviderResponseTooLargeError(
        f"The provider's answer is larger than {max_bytes} bytes.", request=request
    )


class CappedStream(httpx.SyncByteStream):
    """The raw body, refused one chunk past `max_bytes`."""

    def __init__(
        self, inner: httpx.SyncByteStream, max_bytes: int, request: httpx.Request
    ) -> None:
        self._inner: httpx.SyncByteStream = inner
        self._max_bytes: int = max_bytes
        self._request: httpx.Request = request

    def __iter__(self) -> Iterator[bytes]:
        total: int = 0
        for chunk in self._inner:
            total += len(chunk)
            if total > self._max_bytes:
                raise too_large(self._request, self._max_bytes)

            yield chunk

    def close(self) -> None:
        self._inner.close()


class UnpackingCappedStream(httpx.SyncByteStream):
    """A gzip or deflate body, unpacked and refused past `max_bytes`."""

    def __init__(
        self,
        inner: httpx.SyncByteStream,
        max_bytes: int,
        request: httpx.Request,
        encoding: str,
    ) -> None:
        self._inner: httpx.SyncByteStream = inner
        self._max_bytes: int = max_bytes
        self._request: httpx.Request = request
        self._encoding: str = encoding

    def __iter__(self) -> Iterator[bytes]:
        decompressor = zlib.decompressobj(AUTO_DETECT_WBITS)
        is_first: bool = True
        total: int = 0
        try:
            for chunk in self._inner:
                if is_first and self._encoding == "deflate" and not is_zlib(chunk):
                    decompressor = zlib.decompressobj(RAW_DEFLATE_WBITS)
                is_first = False
                # One byte more than allowed is enough to know it is too large.
                unpacked: bytes = decompressor.decompress(
                    chunk, self._max_bytes - total + 1
                )
                total += len(unpacked)
                if total > self._max_bytes or decompressor.unconsumed_tail:
                    raise too_large(self._request, self._max_bytes)

                yield unpacked

            rest: bytes = decompressor.flush()
        except zlib.error:
            raise ProviderResponseEncodingError(
                "The provider sent a damaged compressed answer.", request=self._request
            ) from None

        if total + len(rest) > self._max_bytes:
            raise too_large(self._request, self._max_bytes)

        if rest:
            yield rest

    def close(self) -> None:
        self._inner.close()


def is_zlib(chunk: bytes) -> bool:
    """A zlib header (RFC 1950): CMF/FLG divisible by 31, deflate method."""

    return (
        len(chunk) >= 2
        and chunk[0] & 0x0F == 8
        and (chunk[0] * 256 + chunk[1]) % 31 == 0
    )
