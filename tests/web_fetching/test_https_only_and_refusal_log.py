"""
Tenant addresses are read over https only, and every address the SSRF
guard refuses (the first one, a redirect hop, a webhook target) leaves an
`outbound_fetch_refused` security event naming the refusal and the host,
never the path or query where a feed's secret lives.
"""

import logging

import pytest

from app.clients.http.url_vetting import vet_url
from app.clients.http.webhook_poster import WebhookPoster
from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.integrations.constrained_strings import WebhookTargetUrl
from app.schemas.typings.web_fetching.constrained_strings import WebResourceUrl
from app.utilities.calendar_sync.feed_addresses import fetchable_feed_url
from app.utilities.observability.log_formatting import read_line_fields
from app.utilities.observability.security_events import OUTBOUND_FETCH_REFUSED
from tests.web_fetching.fetch_fakes import (
    PUBLIC_ADDRESS,
    FakeNetwork,
    build_fetcher,
    fetch,
    page,
    redirect,
)

EXPECTED_KEYS: tuple[str, ...] = (
    "security_event",
    "path",
    "reason",
    "client_network",
    "purpose",
    "target_host",
    "message",
)


def refusals(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    lines: list[dict[str, object]] = []
    for record in caplog.records:
        fields: dict[str, object] = read_line_fields(record)
        if fields.get("security_event") == OUTBOUND_FETCH_REFUSED:
            lines.append({**fields, "message": record.getMessage()})
    return lines


@pytest.mark.parametrize(
    ("address", "request_url"),
    [
        ("http://cafe.example/menu?x=1", "https://cafe.example/menu?x=1"),
        ("http://cafe.example:80/", "https://cafe.example/"),
        ("HTTP://Cafe.example", "https://cafe.example/"),
        ("https://cafe.example/", "https://cafe.example/"),
    ],
)
def test_every_address_is_requested_over_https(address: str, request_url: str) -> None:
    vetted = vet_url(address)

    assert (vetted.scheme, vetted.port, vetted.request_url) == (
        "https",
        443,
        request_url,
    )


def test_a_calendar_feed_is_read_over_https_whatever_its_scheme() -> None:
    for address in (
        "webcal://calendar.example/feed.ics?s=secret",
        "http://calendar.example/feed.ics?s=secret",
    ):
        vetted = vet_url(str(fetchable_feed_url(address)))
        assert vetted.request_url == "https://calendar.example/feed.ics?s=secret"


def test_a_redirect_to_plain_http_is_still_read_over_https() -> None:
    network = FakeNetwork(
        {"cafe.example": [PUBLIC_ADDRESS]},
        [redirect("http://cafe.example/home"), page("<p>Menu</p>")],
    )

    fetched = fetch(build_fetcher(network), "https://cafe.example/")

    assert str(fetched.final_url) == "https://cafe.example/home"
    assert network.connections == [(PUBLIC_ADDRESS, 443), (PUBLIC_ADDRESS, 443)]


@pytest.mark.parametrize(
    ("address", "reason", "host"),
    [
        ("http://169.254.169.254/latest/meta-data/", "not_public", "169.254.169.254"),
        ("http://[::1]/", "not_public", "::1"),
        ("http://2130706433/", "not_public", "2130706433"),
        ("https://cafe.example:6379/", "port_not_allowed", "cafe.example"),
        ("http://2130706433/", "not_public", "2130706433"),
        ("http://127.1/", "not_public", "127.1"),
        ("http://0x7f000001/", "not_public", "0x7f000001"),
        ("https://user:pw@cafe.example/", "credentials_in_url", "cafe.example"),
    ],
)
def test_a_refused_address_leaves_a_security_event(
    caplog: pytest.LogCaptureFixture, address: str, reason: str, host: str
) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")

    with pytest.raises(WebFetchError):
        build_fetcher(FakeNetwork({})).vet(WebResourceUrl(address))

    [line] = refusals(caplog)
    assert {key: line.get(key) for key in EXPECTED_KEYS} == {
        "security_event": "outbound_fetch_refused",
        "path": "outbound",
        "reason": reason,
        "client_network": "unknown",
        "purpose": "read",
        "target_host": host,
        "message": f"Security event outbound_fetch_refused: {reason} outbound",
    }


def test_a_redirect_to_the_metadata_address_and_a_rebinding_host_are_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")
    network = FakeNetwork(
        {"cafe.example": [PUBLIC_ADDRESS], "rebind.example": ["10.0.0.7"]},
        [
            redirect("http://169.254.169.254/latest/meta-data/?token=secret"),
            redirect("gopher://cafe.example:70/_secret"),
        ],
    )
    fetcher = build_fetcher(network)

    with pytest.raises(WebFetchError) as redirected:
        fetch(fetcher, "https://cafe.example/")
    with pytest.raises(WebFetchError) as gopher:
        fetch(fetcher, "https://cafe.example/")
    with pytest.raises(WebFetchError) as rebound:
        fetch(fetcher, "https://rebind.example/feed.ics?s=secret")

    assert redirected.value.problem is WebFetchProblem.NOT_PUBLIC
    assert gopher.value.problem is WebFetchProblem.NOT_HTTP
    assert rebound.value.problem is WebFetchProblem.NOT_PUBLIC
    lines = refusals(caplog)
    assert [(line["reason"], line["target_host"]) for line in lines] == [
        ("not_public", "169.254.169.254"),
        ("not_http", "cafe.example"),
        ("not_public", "rebind.example"),
    ]
    assert "secret" not in repr(lines)


def test_an_unreachable_host_is_no_security_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")

    with pytest.raises(WebFetchError) as failed:
        fetch(build_fetcher(FakeNetwork({})), "https://nowhere.example/")

    assert failed.value.problem is WebFetchProblem.UNKNOWN_HOST
    assert refusals(caplog) == []


def test_a_webhook_target_on_a_private_address_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")
    network = FakeNetwork({})
    poster = WebhookPoster(resolver=network.resolve, connector=network.connect)

    result = poster.vet(WebhookTargetUrl("https://127.0.0.1/hooks"))

    assert result is not None
    [line] = refusals(caplog)
    assert (line["purpose"], line["target_host"]) == ("webhook", "127.0.0.1")
