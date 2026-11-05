"""
HTTP as the platform reads the web (website import) and the messaging
platforms' file servers: raw HTTP/1.1 answers, parsed by the real HTTP
stack, are read as RFC 9110 and 9112 define them - equivalent media type
spellings, gzip and chunked bodies (extensions and trailers included),
relative and permanent redirects - and what cannot be read is refused with
its reason; the file servers' documented answers become the media errors.
"""

import gzip
from typing import Any

import httpx
import pytest

from app.clients.http.media_download import download_capped
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from tests.contracts.contract_files import load_json_fixture
from tests.web_fetching.fetch_fakes import (
    HTML_TYPES,
    PUBLIC_ADDRESS,
    FakeNetwork,
    build_fetcher,
    fetch,
)

CRLF: str = "\r\n"
CAFE_URL: str = "https://cafe.example/"
WEB_CASES: list[dict[str, Any]] = load_json_fixture("http", "web_responses.json")[
    "cases"
]
MEDIA_CASES: list[dict[str, Any]] = load_json_fixture("http", "media_cdn_replies.json")[
    "cases"
]
MEDIA_LIMIT: int = 25 * 1024 * 1024


def raw_answer(answer: dict[str, Any]) -> list[bytes]:
    """The bytes a server sends for one fixture answer."""

    head: list[str] = list(answer["head"])
    if "gzip_chunked_body" in answer:
        packed: bytes = gzip.compress(answer["gzip_chunked_body"].encode("utf-8"))
        middle: int = len(packed) // 2
        body: bytes = (
            b"".join(
                f"{len(part):x}".encode() + b"\r\n" + part + b"\r\n"
                for part in (packed[:middle], packed[middle:])
            )
            + b"0\r\n\r\n"
        )
    elif "raw_body" in answer:
        body = answer["raw_body"].encode("latin-1")
    else:
        body = answer["body"].encode("utf-8")
        head.append(f"Content-Length: {len(body)}")
    return [(CRLF.join(head) + CRLF + CRLF).encode("latin-1"), body]


@pytest.mark.parametrize("case", WEB_CASES, ids=lambda case: case["id"])
def test_documented_web_answers_are_read_as_the_rfcs_define(
    case: dict[str, Any],
) -> None:
    answers: list[list[bytes]] = [raw_answer(case)]
    if "then" in case:
        answers.append(raw_answer(case["then"]))
    network = FakeNetwork({"cafe.example": [PUBLIC_ADDRESS]}, answers)
    expected: dict[str, Any] = case["expected"]

    if "detail" in expected:
        with pytest.raises(WebFetchError) as refused:
            fetch(build_fetcher(network), CAFE_URL, HTML_TYPES)
        assert str(refused.value.detail) == expected["detail"]
        return

    resource = fetch(build_fetcher(network), CAFE_URL, HTML_TYPES)

    assert str(resource.media_type) == expected["media_type"]
    assert (None if resource.charset is None else str(resource.charset)) == expected[
        "charset"
    ]
    assert str(resource.final_url) == expected.get("final_url", CAFE_URL)
    if "body" in expected:
        assert resource.body.decode("utf-8") == expected["body"]


@pytest.mark.parametrize("case", MEDIA_CASES, ids=lambda case: case["id"])
def test_file_server_answers_become_media_errors(case: dict[str, Any]) -> None:
    body: bytes = case["body"].encode("latin-1")
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                case["status"], headers=case["headers"], content=body
            )
        )
    )
    url: str = "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=0000"

    if case["expected"] is None:
        content, media_type = download_capped(client, url, {}, MEDIA_LIMIT, "WhatsApp")
        assert (content, media_type) == (body, case["headers"]["Content-Type"])
        return
    with pytest.raises(ApplicationError) as raised:
        download_capped(client, url, {}, MEDIA_LIMIT, "WhatsApp")

    assert type(raised.value).__name__ == case["expected"]
    # The address may carry a signed query or a bot token: never in errors.
    assert "lookaside" not in str(raised.value)
