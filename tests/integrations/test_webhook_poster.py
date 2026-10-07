"""
The webhook poster over a scripted network: public addresses only (the
SSRF guard of every outside address), no redirects followed, and each
answer mapped to a delivery outcome.
"""

from app.clients.http.webhook_poster import WebhookPoster
from app.schemas.constants.integrations import (
    BusinessEventType,
    WebhookDeliveryProblem,
)
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookPostRequest,
    WebhookPostResult,
)
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
    FakeNetwork,
    http_response,
    redirect,
)

HOOK_URL: str = "https://hooks.example.com/workshop"


def post(network: FakeNetwork, url: str = HOOK_URL) -> WebhookPostResult:
    poster = WebhookPoster(resolver=network.resolve, connector=network.connect)
    return poster.post(
        WebhookPostRequest(
            url=WebhookTargetUrl(url),
            body=WebhookPayloadJson('{"type":"lead.created"}'),
            signature=WebhookSignature("t=1790000000,v1=" + "0" * 64),
            event_id=BusinessEventId(),
            event_type=BusinessEventType.LEAD_CREATED,
            delivery_id=WebhookDeliveryId(),
        )
    )


def test_a_2xx_answer_is_a_delivery() -> None:
    network = FakeNetwork({"hooks.example.com": [PUBLIC_ADDRESS]}, [http_response(204)])

    result = post(network)

    assert result.status_code == 204
    assert result.problem is None
    assert network.connections == [(PUBLIC_ADDRESS, 443)]


def test_private_addresses_are_never_connected_to() -> None:
    network = FakeNetwork(
        {
            "hooks.example.com": ["10.0.0.5"],
            "rebind.example.com": ["127.0.0.1"],
            "metadata.example.com": ["169.254.169.254"],
        }
    )

    results = [
        post(network, f"https://{host}/hook")
        for host in ("hooks.example.com", "rebind.example.com", "metadata.example.com")
    ]
    literal = post(network, "https://192.168.1.10/hook")

    assert {result.problem for result in [*results, literal]} == {
        WebhookDeliveryProblem.NOT_PUBLIC
    }
    assert network.connections == []


def test_an_unknown_host_is_named() -> None:
    result = post(FakeNetwork({}))

    assert result.problem is WebhookDeliveryProblem.UNKNOWN_HOST


def test_a_redirect_is_not_followed() -> None:
    network = FakeNetwork(
        {"hooks.example.com": [PUBLIC_ADDRESS]},
        [redirect("http://169.254.169.254/latest/meta-data")],
    )

    result = post(network)

    assert result.status_code == 302
    assert result.problem is WebhookDeliveryProblem.HTTP_STATUS
    assert len(network.connections) == 1


def test_410_gone_and_5xx_are_failures() -> None:
    network = FakeNetwork(
        {"hooks.example.com": [PUBLIC_ADDRESS]},
        [http_response(410), http_response(503)],
    )

    gone, unavailable = post(network), post(network)

    assert gone.problem is WebhookDeliveryProblem.GONE
    assert unavailable.status_code == 503
    assert unavailable.problem is WebhookDeliveryProblem.HTTP_STATUS


def test_vetting_refuses_private_addresses_before_saving() -> None:
    poster = WebhookPoster(resolver=FakeNetwork({}).resolve)

    assert poster.vet(WebhookTargetUrl("https://hooks.example.com/x")) is None
    refused = poster.vet(WebhookTargetUrl("https://localhost/x"))

    assert refused is not None
    assert refused.problem is WebhookDeliveryProblem.NOT_PUBLIC
