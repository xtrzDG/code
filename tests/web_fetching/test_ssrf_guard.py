"""The safe fetcher never connects to anything but a vetted public address."""

import pytest

from app.clients.http.public_addresses import is_public_address
from app.clients.http.url_vetting import vet_url
from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from tests.web_fetching.fetch_fakes import (
    OTHER_PUBLIC_ADDRESS,
    PUBLIC_ADDRESS,
    FakeNetwork,
    build_fetcher,
    fetch,
    page,
    redirect,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.1.2.3/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://[fd00:ec2::254]/latest",
        "http://10.0.0.7/",
        "http://192.168.1.1/",
        "http://100.64.0.1/",
        "http://0.0.0.0/",
        "http://localhost/",
        "https://printer.local/",
        "https://metadata.google.internal/computeMetadata/v1/",
        "https://router.home.arpa/",
    ],
)
def test_private_and_intranet_addresses_are_refused_without_a_lookup(
    url: str,
) -> None:
    network = FakeNetwork({})

    with pytest.raises(WebFetchError) as refused:
        fetch(build_fetcher(network), url)

    assert refused.value.problem is WebFetchProblem.NOT_PUBLIC
    assert str(refused.value.detail) == "not_public"
    assert network.lookups == []
    assert network.connections == []


@pytest.mark.parametrize(
    "addresses",
    [
        ["127.0.0.1"],
        ["169.254.169.254"],
        ["::1"],
        ["10.0.0.7"],
        ["172.20.1.1"],
        ["100.100.100.200"],
        ["fe80::1%eth0"],
        ["::ffff:10.0.0.1"],
        ["64:ff9b::7f00:1"],
        ["2002:7f00:1::1"],
        ["224.0.0.1"],
        [PUBLIC_ADDRESS, "127.0.0.1"],
    ],
)
def test_a_host_resolving_to_any_private_address_is_refused(
    addresses: list[str],
) -> None:
    network = FakeNetwork({"cafe.example": addresses})

    with pytest.raises(WebFetchError) as refused:
        fetch(build_fetcher(network), "https://cafe.example/menu")

    assert refused.value.problem is WebFetchProblem.NOT_PUBLIC
    assert network.lookups == ["cafe.example"]
    assert network.connections == []


def test_a_redirect_to_a_private_address_is_refused() -> None:
    network = FakeNetwork(
        {"cafe.example": [PUBLIC_ADDRESS]},
        [redirect("http://169.254.169.254/latest/meta-data/")],
    )

    with pytest.raises(WebFetchError) as refused:
        fetch(build_fetcher(network), "https://cafe.example/")

    assert refused.value.problem is WebFetchProblem.NOT_PUBLIC
    assert network.connections == [(PUBLIC_ADDRESS, 443)]


def test_a_redirect_to_a_host_resolving_privately_is_refused() -> None:
    network = FakeNetwork(
        {"cafe.example": [PUBLIC_ADDRESS], "intranet.example": ["10.1.2.3"]},
        [redirect("http://intranet.example/admin")],
    )

    with pytest.raises(WebFetchError) as refused:
        fetch(build_fetcher(network), "https://cafe.example/")

    assert refused.value.problem is WebFetchProblem.NOT_PUBLIC
    assert network.lookups == ["cafe.example", "intranet.example"]
    assert network.connections == [(PUBLIC_ADDRESS, 443)]


def test_dns_rebinding_cannot_swap_the_vetted_address() -> None:
    answers: list[list[str]] = [[PUBLIC_ADDRESS], ["127.0.0.1"]]
    network = FakeNetwork(
        {"rebind.example": lambda: answers.pop(0)},
        [page("<p>Hello</p>")],
    )
    fetcher = build_fetcher(network)

    fetched = fetch(fetcher, "http://rebind.example/")

    # One lookup, and the connection went to the very address it vetted.
    assert fetched.body == b"<p>Hello</p>"
    assert network.lookups == ["rebind.example"]
    assert network.connections == [(PUBLIC_ADDRESS, 80)]

    # The next lookup answers a private address: nothing is connected.
    with pytest.raises(WebFetchError) as refused:
        fetch(fetcher, "http://rebind.example/admin")

    assert refused.value.problem is WebFetchProblem.NOT_PUBLIC
    assert network.connections == [(PUBLIC_ADDRESS, 80)]


def test_redirects_are_followed_three_times_at_most() -> None:
    network = FakeNetwork(
        {"cafe.example": [PUBLIC_ADDRESS]},
        [redirect(f"/step-{number}") for number in range(4)],
    )

    with pytest.raises(WebFetchError) as refused:
        fetch(build_fetcher(network), "https://cafe.example/")

    assert refused.value.problem is WebFetchProblem.TOO_MANY_REDIRECTS
    assert len(network.connections) == 4


def test_a_followed_redirect_reports_where_the_page_came_from() -> None:
    network = FakeNetwork(
        {"cafe.example": [PUBLIC_ADDRESS], "www.cafe.example": [OTHER_PUBLIC_ADDRESS]},
        [redirect("https://www.cafe.example/home", 301), page("<h1>Cafe</h1>")],
    )

    fetched = fetch(build_fetcher(network), "http://cafe.example/")

    assert str(fetched.url) == "http://cafe.example/"
    assert str(fetched.final_url) == "https://www.cafe.example/home"
    assert str(fetched.charset) == "utf-8"
    assert network.connections == [(PUBLIC_ADDRESS, 80), (OTHER_PUBLIC_ADDRESS, 443)]


@pytest.mark.parametrize(
    ("url", "problem"),
    [
        ("ftp://cafe.example/menu", WebFetchProblem.NOT_HTTP),
        ("file:///etc/passwd", WebFetchProblem.NOT_HTTP),
        ("gopher://cafe.example:70/", WebFetchProblem.NOT_HTTP),
        ("http://:80/", WebFetchProblem.NOT_HTTP),
        ("http://cafe.example:99999/", WebFetchProblem.NOT_HTTP),
        ("http://user:secret@cafe.example/", WebFetchProblem.CREDENTIALS_IN_URL),
        ("https://cafe.example:8443/", WebFetchProblem.PORT_NOT_ALLOWED),
        ("http://cafe.example:22/", WebFetchProblem.PORT_NOT_ALLOWED),
        ("http://cafe.example:6379/", WebFetchProblem.PORT_NOT_ALLOWED),
    ],
)
def test_only_http_on_standard_ports_without_credentials(
    url: str, problem: WebFetchProblem
) -> None:
    with pytest.raises(WebFetchError) as refused:
        vet_url(url)

    assert refused.value.problem is problem


def test_standard_ports_and_international_names_pass_the_static_check() -> None:
    assert vet_url("http://cafe.example:443/a?b=1#top").request_url == (
        "http://cafe.example:443/a?b=1"
    )
    assert vet_url("https://CAFE.example").request_url == "https://cafe.example/"
    vetted = vet_url("https://кафе.example/меню")
    assert vetted.host == "xn--80akn5b.example"
    assert vetted.request_url == (
        "https://xn--80akn5b.example/%D0%BC%D0%B5%D0%BD%D1%8E"
    )
    assert vetted.port == 443


def test_an_unknown_host_is_reported_as_such() -> None:
    network = FakeNetwork({})

    with pytest.raises(WebFetchError) as failed:
        fetch(build_fetcher(network), "https://nowhere.example/")

    assert failed.value.problem is WebFetchProblem.UNKNOWN_HOST
    assert network.connections == []


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        (PUBLIC_ADDRESS, True),
        ("2606:4700:4700::1111", True),
        ("::ffff:93.184.216.34", True),
        ("100.64.0.1", False),
        ("192.0.0.192", False),
        ("198.18.0.1", False),
        ("255.255.255.255", False),
        ("not an address", False),
    ],
)
def test_public_address_policy(address: str, expected: bool) -> None:
    assert is_public_address(address) is expected
