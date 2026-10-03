"""Menu links: read through the safe fetcher; unreadable links name their problem."""

import httpcore
import pytest

from app.adapters.llm.menu_extraction.menu_extraction_adapter import (
    MenuExtractionAdapter,
)
from app.clients.http.safe_http_fetcher import SafeHttpFetcher
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from tests.brain.menu_extraction_helpers import (
    build_adapter,
    link_reasons,
    link_request,
)
from tests.brain.provider_http_fakes import ScriptedHttp, build_openai_client
from tests.web_fetching.fetch_fakes import (
    PUBLIC_ADDRESS,
    FakeNetwork,
    http_response,
    redirect,
)

CAFE: dict[str, list[str]] = {"cafe.example": [PUBLIC_ADDRESS]}


@pytest.mark.parametrize(
    ("url", "addresses"),
    [
        ("http://localhost:80/menu", None),
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
    host: str = url.split("/")[2]
    network = FakeNetwork({} if addresses is None else {host: addresses})
    adapter = build_adapter(ScriptedHttp([]), network)

    with pytest.raises(ValidationFailedError, match="public address") as refused:
        adapter.extract(link_request(url))

    assert link_reasons(refused.value) == [("menu_link_invalid", ["not_public"])]
    assert network.connections == []


def test_redirects_to_private_addresses_are_refused_too() -> None:
    network = FakeNetwork(CAFE, [redirect("http://localhost/admin")])
    adapter = build_adapter(ScriptedHttp([]), network)

    with pytest.raises(ValidationFailedError, match="public address"):
        adapter.extract(link_request())

    assert network.connections == [(PUBLIC_ADDRESS, 443)]


@pytest.mark.parametrize(
    ("answers", "url", "expected"),
    [
        (
            [http_response(404)],
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["http_status:404"]),
        ),
        (
            [[b"garbled\r\n\r\n"]],
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["request_failed"]),
        ),
        (
            [http_response(302)],
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["redirect_without_location"]),
        ),
        (
            [redirect("/again") for _ in range(4)],
            "https://cafe.example/menu",
            ("menu_link_unreachable", ["too_many_redirects"]),
        ),
        (
            [http_response(200, {"Content-Type": "application/zip"}, b"PK")],
            "https://cafe.example/menu.zip",
            ("menu_link_unreadable", ["media_type:application/zip"]),
        ),
        (
            [redirect("ftp://cafe.example/menu")],
            "https://cafe.example/menu",
            ("menu_link_invalid", ["not_http"]),
        ),
        (
            [],
            "https://cafe.example:8443/menu",
            ("menu_link_invalid", ["port_not_allowed"]),
        ),
    ],
)
def test_links_that_cannot_be_read_name_a_distinct_problem(
    answers: list[list[bytes]],
    url: str,
    expected: tuple[str, list[str]],
) -> None:
    http = ScriptedHttp([])
    adapter = build_adapter(http, FakeNetwork(CAFE, answers))

    with pytest.raises(ValidationFailedError) as refused:
        adapter.extract(link_request(url))

    assert link_reasons(refused.value) == [expected]
    assert http.requests == []


@pytest.mark.parametrize(
    ("failure", "detail"),
    [
        (httpcore.ConnectTimeout("slow"), "timeout"),
        (httpcore.ConnectError("refused"), "connection_failed"),
    ],
)
def test_connection_failures_name_their_problem(
    failure: Exception, detail: str
) -> None:
    def fail(address: str, port: int, timeout: float | None) -> httpcore.NetworkStream:
        raise failure

    adapter = MenuExtractionAdapter(
        client=build_openai_client(ScriptedHttp([])),
        model_id=LlmModelId("gpt-5-mini"),
        page_fetcher=SafeHttpFetcher(
            resolver=lambda host: [PUBLIC_ADDRESS], connector=fail
        ),
    )

    with pytest.raises(ValidationFailedError) as refused:
        adapter.extract(link_request())

    assert link_reasons(refused.value) == [("menu_link_unreachable", [detail])]


def test_unknown_hosts_and_huge_menus_name_their_problem() -> None:
    unknown = build_adapter(ScriptedHttp([]), FakeNetwork({}))
    huge = build_adapter(
        ScriptedHttp([]),
        FakeNetwork(CAFE, [http_response(200, {"Content-Length": "20000000"})]),
    )

    with pytest.raises(ValidationFailedError) as unknown_host:
        unknown.extract(link_request())
    with pytest.raises(ValidationFailedError) as too_large:
        huge.extract(link_request())

    assert link_reasons(unknown_host.value) == [
        ("menu_link_unreachable", ["unknown_host"])
    ]
    assert link_reasons(too_large.value) == [("menu_link_unreadable", ["too_large"])]
