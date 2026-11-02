"""
The shared provider client (OWASP API10): certificates verified, timeouts
set, redirects returned instead of followed, and answers read within a
cap counted after unpacking. A provider that answers too much, or a
compressed bomb, fails like a broken connection, which the clients turn
into their ExternalServiceError: nothing is held in memory past the cap.
"""

import gzip
import zlib
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

from app.clients.google.google_http import GoogleHttp
from app.clients.http.capped_response_stream import (
    ProviderResponseEncodingError,
    ProviderResponseTooLargeError,
)
from app.clients.http.provider_http_client import (
    API_RESPONSE_MAX_BYTES,
    build_provider_http_client,
)
from app.clients.stripe.stripe_client import StripeClient
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.strings import PlatformSecret

CAP: int = 1_000


class Chunks(httpx.SyncByteStream):
    """A body that arrives in pieces, as from a real connection."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks: list[bytes] = chunks

    def __iter__(self) -> Iterator[bytes]:
        yield from self._chunks


def answering(
    body: bytes, headers: dict[str, str] | None = None, status: int = 200
) -> Callable[[httpx.Request], httpx.Response]:
    def handle(request: httpx.Request) -> httpx.Response:
        del request
        middle: int = len(body) // 2
        return httpx.Response(
            status, headers=headers or {}, stream=Chunks([body[:middle], body[middle:]])
        )

    return handle


def client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return build_provider_http_client(
        timeout=5.0,
        max_response_bytes=CAP,
        base_url="https://api.provider.example",
        transport=httpx.MockTransport(handler),
    )


def test_the_client_verifies_certificates_and_has_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built_with: dict[str, object] = {}

    class RecordingClient(httpx.Client):
        def __init__(self, **options: Any) -> None:
            built_with.update(options)
            super().__init__(**options)

    monkeypatch.setattr(httpx, "Client", RecordingClient)
    built = build_provider_http_client(timeout=7.0, max_response_bytes=CAP)

    assert built_with["verify"] is True
    assert built_with["follow_redirects"] is False
    assert built.follow_redirects is False
    assert (built.timeout.connect, built.timeout.read) == (7.0, 7.0)
    assert built.headers["Accept-Encoding"] == "gzip, deflate"


def test_a_redirect_is_returned_not_followed() -> None:
    seen: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            302, headers={"Location": "http://169.254.169.254/latest/meta-data/"}
        )

    response = client(handle).get("/v1/invoices/in_1")

    assert response.status_code == 302
    assert seen == ["https://api.provider.example/v1/invoices/in_1"]


def test_answers_within_the_cap_are_read_as_usual() -> None:
    plain = client(answering(b'{"id": "in_1"}')).get("/x")
    packed = client(
        answering(gzip.compress(b'{"id": "in_2"}'), {"Content-Encoding": "gzip"})
    ).get("/x")
    deflated = client(
        answering(zlib.compress(b'{"id": "in_3"}'), {"Content-Encoding": "deflate"})
    ).get("/x")
    raw_deflate = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    raw = raw_deflate.compress(b'{"id": "in_4"}') + raw_deflate.flush()
    raw_deflated = client(answering(raw, {"Content-Encoding": "deflate"})).get("/x")

    assert [plain.json(), packed.json(), deflated.json(), raw_deflated.json()] == [
        {"id": "in_1"},
        {"id": "in_2"},
        {"id": "in_3"},
        {"id": "in_4"},
    ]


@pytest.mark.parametrize(
    ("body", "headers"),
    [
        (b"x" * (CAP + 1), {}),
        (b"x" * (CAP + 1), {"Content-Length": str(CAP + 1)}),
        (gzip.compress(b"0" * 10_000_000), {"Content-Encoding": "gzip"}),
        (zlib.compress(b"0" * 10_000_000), {"Content-Encoding": "deflate"}),
    ],
    ids=["streamed", "declared", "gzip bomb", "deflate bomb"],
)
def test_an_answer_over_the_cap_fails_like_a_broken_connection(
    body: bytes, headers: dict[str, str]
) -> None:
    with pytest.raises(ProviderResponseTooLargeError) as refused:
        client(answering(body, headers)).get("/x")

    assert isinstance(refused.value, httpx.ReadError)


def test_a_streamed_download_stops_at_the_cap() -> None:
    read: list[int] = []
    with (
        pytest.raises(ProviderResponseTooLargeError),
        client(answering(b"y" * (CAP * 5))).stream("GET", "/file") as response,
    ):
        for chunk in response.iter_bytes():
            read.append(len(chunk))

    assert sum(read) <= CAP


@pytest.mark.parametrize(
    ("body", "headers"),
    [
        (b"not gzip at all", {"Content-Encoding": "gzip"}),
        (b"\x1b\x00", {"Content-Encoding": "br"}),
        (b"\x28\xb5\x2f\xfd", {"Content-Encoding": "zstd"}),
    ],
)
def test_damaged_or_unread_codings_are_refused(
    body: bytes, headers: dict[str, str]
) -> None:
    with pytest.raises(ProviderResponseEncodingError) as refused:
        client(answering(body, headers)).get("/x")

    assert isinstance(refused.value, httpx.HTTPError)


def test_a_client_needs_a_positive_cap() -> None:
    with pytest.raises(ValueError, match="positive"):
        build_provider_http_client(timeout=1.0, max_response_bytes=0)


def test_stripe_turns_an_oversized_answer_into_a_provider_failure() -> None:
    stripe = StripeClient(
        secret_key=PlatformSecret("sk_test_cap"),
        webhook_secret=PlatformSecret("whsec_cap"),
        transport=httpx.MockTransport(
            answering(b'{"id": "' + b"a" * API_RESPONSE_MAX_BYTES + b'"}')
        ),
    )

    with pytest.raises(ExternalServiceError, match="ReadError|TooLarge"):
        stripe.retrieve_invoice("in_1")


def test_google_turns_a_compressed_bomb_into_a_provider_failure() -> None:
    bomb: bytes = gzip.compress(b" " * (API_RESPONSE_MAX_BYTES * 2))
    google = GoogleHttp(
        httpx.MockTransport(answering(bomb, {"Content-Encoding": "gzip"}))
    )

    with pytest.raises(ExternalServiceError, match="TooLarge"):
        google.post_form("https://oauth2.example/token", {"code": "x"}, "Token")
