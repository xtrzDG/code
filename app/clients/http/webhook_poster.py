"""
Posting signed webhooks to the receivers businesses chose, through the
same SSRF guard as every other outside address (`url_vetting`,
`VettingNetworkBackend`): public addresses only, the vetted address
connected to, no redirects followed, a bounded time and answer size.
"""

import ssl
import time
from collections.abc import Callable

import httpcore

from app.clients.http.url_vetting import VettedUrl, vet_url
from app.clients.http.vetting_network_backend import (
    HostResolver,
    TcpConnector,
    VettingNetworkBackend,
    connect_tcp_address,
    resolve_host_addresses,
)
from app.contracts.integrations import WebhookPosterContract
from app.schemas.constants.integrations import WebhookDeliveryProblem
from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookPostRequest,
    WebhookPostResult,
)
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.integrations.constrained_strings import (
    WebhookErrorText,
    WebhookTargetUrl,
)
from app.schemas.typings.observability.constrained_integers import HttpStatusCode
from app.utilities.integrations.webhook_signatures import (
    DELIVERY_ID_HEADER,
    EVENT_ID_HEADER,
    EVENT_TYPE_HEADER,
    SIGNATURE_HEADER,
)

USER_AGENT: str = "AssistantWorkshop-Webhooks/1.0"
TIMEOUT_SECONDS: float = 10.0
# The answer's body is read (so the connection ends cleanly) and dropped.
MAX_ANSWER_BYTES: int = 64 * 1024
REFUSALS: dict[WebFetchProblem, WebhookDeliveryProblem] = {
    WebFetchProblem.UNKNOWN_HOST: WebhookDeliveryProblem.UNKNOWN_HOST,
    WebFetchProblem.TIMEOUT: WebhookDeliveryProblem.TIMEOUT,
    WebFetchProblem.CONNECTION_FAILED: WebhookDeliveryProblem.CONNECTION_FAILED,
}


class WebhookPoster(WebhookPosterContract):
    """
    Sends one POST per call over a fresh connection to the vetted address.
    `resolver`, `connector` and `clock` are replaceable for tests; the
    receiver's TLS certificate is checked as for any https request.
    """

    def __init__(
        self,
        resolver: HostResolver = resolve_host_addresses,
        connector: TcpConnector = connect_tcp_address,
        ssl_context: ssl.SSLContext | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backend: VettingNetworkBackend = VettingNetworkBackend(
            resolver, connector
        )
        self._ssl_context: ssl.SSLContext | None = ssl_context
        self._clock: Callable[[], float] = clock

    def vet(self, url: WebhookTargetUrl) -> WebhookPostResult | None:
        try:
            vet_url(str(url))
        except WebFetchError as error:
            return refused(error)

        return None

    def post(self, request: WebhookPostRequest) -> WebhookPostResult:
        try:
            vetted: VettedUrl = vet_url(str(request.url))
            return self._post(vetted, request)
        except WebFetchError as error:
            return refused(error)
        except httpcore.TimeoutException:
            return failure(WebhookDeliveryProblem.TIMEOUT, "The address took too long.")
        except httpcore.ConnectError:
            return failure(
                WebhookDeliveryProblem.CONNECTION_FAILED,
                "The address cannot be reached.",
            )
        except httpcore.NetworkError, httpcore.ProtocolError, OSError:
            return failure(
                WebhookDeliveryProblem.REQUEST_FAILED,
                "The request failed on its way to the address.",
            )

    def _post(
        self, vetted: VettedUrl, request: WebhookPostRequest
    ) -> WebhookPostResult:
        deadline: float = self._clock() + TIMEOUT_SECONDS
        body: bytes = str(request.body).encode()
        with (
            httpcore.ConnectionPool(
                ssl_context=self._ssl_context,
                network_backend=self._backend,
                max_connections=1,
                retries=0,
            ) as pool,
            pool.stream(
                "POST",
                vetted.request_url,
                headers=[
                    (b"User-Agent", USER_AGENT.encode()),
                    (b"Content-Type", b"application/json"),
                    (b"Content-Length", str(len(body)).encode()),
                    (SIGNATURE_HEADER.encode(), str(request.signature).encode()),
                    (EVENT_ID_HEADER.encode(), str(request.event_id).encode()),
                    (EVENT_TYPE_HEADER.encode(), request.event_type.value.encode()),
                    (DELIVERY_ID_HEADER.encode(), str(request.delivery_id).encode()),
                ],
                content=body,
                extensions={
                    "timeout": {
                        "connect": TIMEOUT_SECONDS,
                        "read": TIMEOUT_SECONDS,
                        "write": TIMEOUT_SECONDS,
                        "pool": TIMEOUT_SECONDS,
                    }
                },
            ) as response,
        ):
            drain(response, deadline, self._clock)
            return answered(response.status)


def drain(
    response: httpcore.Response, deadline: float, clock: Callable[[], float]
) -> None:
    """Read the answer's body up to the limit and the deadline, dropping it."""

    received: int = 0
    for chunk in response.iter_stream():
        received += len(chunk)
        if received > MAX_ANSWER_BYTES or clock() > deadline:
            return


def answered(status: int) -> WebhookPostResult:
    if not 100 <= status <= 599:
        return failure(
            WebhookDeliveryProblem.REQUEST_FAILED,
            f"The address answered with a status that is not HTTP ({status}).",
        )

    code = HttpStatusCode(status)
    if 200 <= status < 300:
        return WebhookPostResult(status_code=code)

    if status == 410:
        return WebhookPostResult(
            status_code=code,
            problem=WebhookDeliveryProblem.GONE,
            error=WebhookErrorText("The address answered 410 Gone."),
        )

    return WebhookPostResult(
        status_code=code,
        problem=WebhookDeliveryProblem.HTTP_STATUS,
        error=WebhookErrorText(f"The address answered HTTP {status}."),
    )


def refused(error: WebFetchError) -> WebhookPostResult:
    problem: WebhookDeliveryProblem = REFUSALS.get(
        error.problem, WebhookDeliveryProblem.NOT_PUBLIC
    )
    return failure(problem, str(error))


def failure(problem: WebhookDeliveryProblem, message: str) -> WebhookPostResult:
    return WebhookPostResult(
        problem=problem, error=WebhookErrorText(" ".join(message.split())[:300])
    )
