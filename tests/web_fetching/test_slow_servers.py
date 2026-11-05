"""
A server that answers a byte at a time cannot hold a request past its
deadline: every read and write on the connection is cut to the time left
(the website reader and the webhook poster alike).
"""

from ssl import PROTOCOL_TLS_CLIENT, SSLContext

import httpcore
import pytest

from app.clients.http.deadline_network_stream import DeadlineNetworkStream
from app.clients.http.safe_http_fetcher import SafeHttpFetcher
from app.clients.http.webhook_poster import TIMEOUT_SECONDS, WebhookPoster
from app.schemas.constants.integrations import (
    BusinessEventType,
    WebhookDeliveryProblem,
)
from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.dto.integrations.webhook_attempts import WebhookPostRequest
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.integrations.constrained_strings import (
    WebhookSignature,
    WebhookTargetUrl,
)
from app.schemas.typings.integrations.prefixed_id import (
    BusinessEventId,
    WebhookDeliveryId,
)
from app.schemas.typings.integrations.strings import WebhookPayloadJson
from tests.web_fetching.fetch_fakes import (
    PUBLIC_ADDRESS,
    SteppingClock,
    fetch,
)

STATUS_LINE: bytes = b"HTTP/1.1 200 OK\r\n"
# One header line after another, never the blank line that ends them.
ENDLESS_HEADER: bytes = b"X-Pad: 1\r\n"


class TricklingStream(httpcore.NetworkStream):
    """A server sending the status line, then a header line per read, forever."""

    def __init__(self) -> None:
        self.reads: int = 0
        self.timeouts: list[float | None] = []

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        del max_bytes
        self.reads += 1
        self.timeouts.append(timeout)
        return STATUS_LINE if self.reads == 1 else ENDLESS_HEADER

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        del buffer
        self.timeouts.append(timeout)

    def close(self) -> None:
        return None

    def start_tls(
        self,
        ssl_context: SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.NetworkStream:
        del ssl_context, server_hostname, timeout
        return self


class TricklingNetwork:
    """DNS and connections of one public host that trickles its answer."""

    def __init__(self) -> None:
        self.stream: TricklingStream = TricklingStream()
        self.connect_timeouts: list[float | None] = []

    def resolve(self, host: str) -> list[str]:
        del host
        return [PUBLIC_ADDRESS]

    def connect(
        self, address: str, port: int, timeout: float | None
    ) -> httpcore.NetworkStream:
        del address, port
        self.connect_timeouts.append(timeout)
        return self.stream


def test_the_website_reader_gives_up_at_its_deadline() -> None:
    network = TricklingNetwork()
    fetcher = SafeHttpFetcher(
        resolver=network.resolve, connector=network.connect, clock=SteppingClock(1.0)
    )

    with pytest.raises(WebFetchError) as refused:
        fetch(fetcher, "https://slow.example/", timeout_seconds=10.0)

    assert refused.value.problem is WebFetchProblem.TIMEOUT
    # A second passes per clock reading: about ten reads fit, not thousands.
    assert network.stream.reads < 12
    assert all(
        timeout is not None and timeout <= 10.0 for timeout in network.stream.timeouts
    )


def test_a_webhook_receiver_cannot_hold_the_delivery() -> None:
    network = TricklingNetwork()
    poster = WebhookPoster(
        resolver=network.resolve, connector=network.connect, clock=SteppingClock(1.0)
    )

    result = poster.post(
        WebhookPostRequest(
            url=WebhookTargetUrl("https://hooks.example.com/slow"),
            body=WebhookPayloadJson('{"type":"lead.created"}'),
            signature=WebhookSignature("t=1790000000,v1=" + "0" * 64),
            event_id=BusinessEventId(),
            event_type=BusinessEventType.LEAD_CREATED,
            delivery_id=WebhookDeliveryId(),
        )
    )

    assert result.problem is WebhookDeliveryProblem.TIMEOUT
    assert network.stream.reads < int(TIMEOUT_SECONDS) + 2
    assert network.connect_timeouts[0] is not None
    assert network.connect_timeouts[0] <= TIMEOUT_SECONDS


def test_each_operation_gets_the_time_left_and_none_past_the_deadline() -> None:
    inner = TricklingStream()
    now: list[float] = [100.0]
    stream = DeadlineNetworkStream(inner, deadline=105.0, clock=lambda: now[0])

    stream.write(b"GET / HTTP/1.1\r\n\r\n", timeout=30.0)
    secured = stream.start_tls(
        SSLContext(PROTOCOL_TLS_CLIENT), "slow.example", timeout=2.0
    )
    now[0] = 104.0
    secured.read(1024, timeout=None)
    now[0] = 105.0

    with pytest.raises(httpcore.ReadTimeout):
        secured.read(1024, timeout=30.0)
    with pytest.raises(httpcore.WriteTimeout):
        stream.write(b"more", timeout=30.0)
    assert inner.timeouts == [5.0, 1.0]
    assert isinstance(secured, DeadlineNetworkStream)
    assert secured.get_extra_info("server_addr") is None
