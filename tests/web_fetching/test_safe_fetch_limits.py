"""The safe fetcher's size, time, media type, encoding and status limits."""

import zlib

import httpcore
import pytest

from app.clients.http.safe_http_fetcher import SafeHttpFetcher
from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.web_fetching.constrained_strings import WebMediaType
from tests.web_fetching.fetch_fakes import (
    PUBLIC_ADDRESS,
    FakeNetwork,
    SteppingClock,
    build_fetcher,
    fetch,
    gzipped_page,
    http_response,
    page,
)

CAFE: dict[str, list[str]] = {"cafe.example": [PUBLIC_ADDRESS]}


def refusal(network: FakeNetwork, **options: object) -> WebFetchError:
    with pytest.raises(WebFetchError) as refused:
        fetch(build_fetcher(network), "https://cafe.example/", **options)  # type: ignore[arg-type]

    return refused.value


def test_an_error_status_names_the_status() -> None:
    error = refusal(FakeNetwork(CAFE, [http_response(404)]))

    assert error.problem is WebFetchProblem.HTTP_STATUS
    assert str(error.detail) == "http_status:404"


def test_a_redirect_without_a_location_fails() -> None:
    error = refusal(FakeNetwork(CAFE, [http_response(302)]))

    assert error.problem is WebFetchProblem.REDIRECT_WITHOUT_LOCATION


def test_only_the_requested_media_types_are_accepted() -> None:
    zipped = http_response(200, {"Content-Type": "application/zip"}, b"PK")

    error = refusal(FakeNetwork(CAFE, [zipped]))

    assert error.problem is WebFetchProblem.UNSUPPORTED_MEDIA_TYPE
    assert str(error.detail) == "media_type:application/zip"


def test_an_odd_content_type_is_not_trusted() -> None:
    odd = http_response(200, {"Content-Type": "text/html<script>"}, b"x")

    error = refusal(FakeNetwork(CAFE, [odd]))

    assert error.problem is WebFetchProblem.UNSUPPORTED_MEDIA_TYPE


def test_a_page_without_content_type_is_read_as_html() -> None:
    answer = [b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\r\n", b"<p/>"]
    fetched = fetch(build_fetcher(FakeNetwork(CAFE, [answer])), "https://cafe.example/")

    assert str(fetched.media_type) == "text/html"
    assert fetched.charset is None


def test_a_declared_length_above_the_limit_is_refused_before_reading() -> None:
    declared = http_response(200, {"Content-Length": "6000000"}, b"")

    error = refusal(FakeNetwork(CAFE, [declared]))

    assert error.problem is WebFetchProblem.TOO_LARGE
    assert "5 MB" in str(error)


def test_a_body_above_the_limit_is_refused_while_reading() -> None:
    chunked = [
        b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n",
        b"400\r\n" + b"a" * 1024 + b"\r\n",
        b"400\r\n" + b"a" * 1024 + b"\r\n",
        b"0\r\n\r\n",
    ]

    error = refusal(FakeNetwork(CAFE, [chunked]), max_bytes=1500)

    assert error.problem is WebFetchProblem.TOO_LARGE


def test_a_compressed_page_is_unpacked() -> None:
    fetched = fetch(
        build_fetcher(FakeNetwork(CAFE, [gzipped_page(b"<h1>Menu</h1>")])),
        "https://cafe.example/",
    )

    assert fetched.body == b"<h1>Menu</h1>"


def test_a_compression_bomb_is_stopped_at_the_limit() -> None:
    bomb: bytes = zlib.compress(b"\0" * 50_000_000, 9)
    answer = http_response(200, {"Content-Encoding": "deflate"}, bomb)

    error = refusal(FakeNetwork(CAFE, [answer]))

    assert len(bomb) < 100_000
    assert error.problem is WebFetchProblem.TOO_LARGE


@pytest.mark.parametrize(
    ("encoding", "body"),
    [("br", b"\x1b\x00"), ("gzip", b"not gzip at all")],
)
def test_unknown_or_damaged_encodings_are_refused(encoding: str, body: bytes) -> None:
    answer = http_response(200, {"Content-Encoding": encoding}, body)

    error = refusal(FakeNetwork(CAFE, [answer]))

    assert error.problem is WebFetchProblem.UNSUPPORTED_ENCODING


def test_the_whole_fetch_has_one_deadline() -> None:
    network = FakeNetwork(CAFE, [page("<p>slow</p>")])
    fetcher = build_fetcher(network, clock=SteppingClock(step=6.0))

    with pytest.raises(WebFetchError) as refused:
        fetch(fetcher, "https://cafe.example/")

    assert refused.value.problem is WebFetchProblem.TIMEOUT


@pytest.mark.parametrize(
    ("failure", "problem"),
    [
        (httpcore.ConnectTimeout("slow"), WebFetchProblem.TIMEOUT),
        (httpcore.ConnectError("refused"), WebFetchProblem.CONNECTION_FAILED),
        (ConnectionRefusedError("refused"), WebFetchProblem.CONNECTION_FAILED),
    ],
)
def test_connection_failures_are_named(
    failure: Exception, problem: WebFetchProblem
) -> None:
    def fail(address: str, port: int, timeout: float | None) -> httpcore.NetworkStream:
        raise failure

    fetcher = SafeHttpFetcher(resolver=lambda host: [PUBLIC_ADDRESS], connector=fail)

    with pytest.raises(WebFetchError) as refused:
        fetch(fetcher, "https://cafe.example/")

    assert refused.value.problem is problem


def test_every_vetted_address_is_tried_in_turn() -> None:
    tried: list[str] = []

    def connect(
        address: str, port: int, timeout: float | None
    ) -> httpcore.NetworkStream:
        tried.append(address)
        if address == "2606:4700:4700::1111":
            raise OSError("network unreachable")

        return httpcore.MockStream(page("<p>ok</p>"))

    fetcher = SafeHttpFetcher(
        resolver=lambda host: ["2606:4700:4700::1111", PUBLIC_ADDRESS],
        connector=connect,
    )

    fetched = fetch(fetcher, "https://cafe.example/")

    assert fetched.body == b"<p>ok</p>"
    assert tried == ["2606:4700:4700::1111", PUBLIC_ADDRESS]


def test_a_broken_answer_is_a_failed_request() -> None:
    error = refusal(FakeNetwork(CAFE, [[b"NOT HTTP AT ALL\r\n\r\n"]]))

    assert error.problem is WebFetchProblem.REQUEST_FAILED


def test_a_charset_is_read_from_the_content_type() -> None:
    answer = http_response(
        200, {"Content-Type": 'text/plain; Charset="Windows-1251"'}, b"\xcc\xe5\xed\xfe"
    )
    fetched = fetch(
        build_fetcher(FakeNetwork(CAFE, [answer])),
        "https://cafe.example/",
        media_types=frozenset({WebMediaType("text/plain")}),
    )

    assert str(fetched.charset) == "windows-1251"
    assert fetched.body.decode(str(fetched.charset)) == "Меню"
