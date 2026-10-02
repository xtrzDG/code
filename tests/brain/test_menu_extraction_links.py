"""Menu links: private addresses are refused; unreadable links name their problem."""

from typing import Any

import httpx
import pytest

from app.adapters.llm.menu_extraction.menu_extraction_adapter import (
    MenuExtractionAdapter,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.menu_import.constrained_strings import MenuSourceMediaType
from tests.brain.menu_extraction_helpers import (
    build_adapter,
    extraction_request,
    fail_with,
    link_reasons,
    link_request,
    respond,
)
from tests.brain.provider_http_fakes import ScriptedHttp, build_openai_client


@pytest.mark.parametrize(
    ("url", "addresses"),
    [
        ("http://localhost:8000/menu", None),
        ("https://printer.local/menu", None),
        ("https://intranet.example/menu", ["10.0.0.7"]),
        ("https://metadata.example/latest", ["169.254.169.254"]),
        ("https://loop.example/menu", ["127.0.0.1"]),
        ("https://v6.example/menu", ["::1"]),
    ],
)
def test_links_to_private_addresses_are_refused(
    url: str,
    addresses: list[str] | None,
) -> None:
    def never(request: httpx.Request) -> httpx.Response:
        raise AssertionError("A private address must not be fetched.")

    adapter = build_adapter(ScriptedHttp([]), never, addresses)

    with pytest.raises(ValidationFailedError, match="public address") as refused:
        adapter.extract(
            extraction_request(
                media_type=MenuSourceMediaType("text/html"),
                data_base64=None,
                url=WebLink(url),
            )
        )

    assert link_reasons(refused.value) == [("menu_link_invalid", ["not_public"])]


def test_redirects_to_private_addresses_are_refused_too() -> None:
    def serve(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://localhost/admin"})

    adapter = build_adapter(ScriptedHttp([]), serve)

    with pytest.raises(ValidationFailedError, match="public address"):
        adapter.extract(
            extraction_request(
                media_type=MenuSourceMediaType("text/html"),
                data_base64=None,
                url=WebLink("https://cafe.example/menu"),
            )
        )


@pytest.mark.parametrize(
    ("page_handler", "addresses", "url", "expected"),
    [
        (
            respond(404),
            None,
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["http_status:404"]),
        ),
        (
            fail_with(httpx.ConnectTimeout("slow")),
            None,
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["timeout"]),
        ),
        (
            fail_with(httpx.ConnectError("refused")),
            None,
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["connection_failed"]),
        ),
        (
            fail_with(httpx.RemoteProtocolError("garbled")),
            None,
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["request_failed"]),
        ),
        (
            respond(302),
            None,
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["redirect_without_location"]),
        ),
        (
            respond(302, {"location": "/again"}),
            None,
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["too_many_redirects"]),
        ),
        (
            respond(200, {"content-type": "application/zip"}, b"PK"),
            None,
            "https://cafe.example/menu.zip",
            ("menu_link_unreadable", ["media_type:application/zip"]),
        ),
        (
            respond(302, {"location": "ftp://cafe.example/menu"}),
            None,
            "https://cafe.example/menu",
            ("menu_link_invalid", ["not_http"]),
        ),
    ],
)
def test_links_that_cannot_be_read_name_a_distinct_problem(
    page_handler: Any,
    addresses: list[str] | None,
    url: str,
    expected: tuple[str, list[str]],
) -> None:
    http = ScriptedHttp([])
    adapter = build_adapter(http, page_handler, addresses)

    with pytest.raises(ValidationFailedError) as refused:
        adapter.extract(link_request(url))

    assert link_reasons(refused.value) == [expected]
    assert http.requests == []


def test_unknown_hosts_and_huge_pages_name_their_problem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unknown(host: str) -> list[str]:
        raise OSError(f"no such host {host}")

    adapter = MenuExtractionAdapter(
        client=build_openai_client(ScriptedHttp([])),
        model_id=LlmModelId("gpt-5-mini"),
        page_transport=httpx.MockTransport(respond(200)),
        host_resolver=unknown,
    )
    with pytest.raises(ValidationFailedError) as unknown_host:
        adapter.extract(link_request())

    monkeypatch.setattr(
        "app.adapters.llm.menu_extraction.menu_page_download.MAX_PAGE_BYTES", 8
    )
    huge = build_adapter(
        ScriptedHttp([]),
        respond(200, {"content-type": "text/html"}, b"<p>long menu</p>"),
    )
    with pytest.raises(ValidationFailedError) as too_large:
        huge.extract(link_request())

    assert link_reasons(unknown_host.value) == [
        ("menu_link_unreachable", ["unknown_host"])
    ]
    assert link_reasons(too_large.value) == [("menu_link_unreadable", ["too_large"])]
