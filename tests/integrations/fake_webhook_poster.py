"""
The webhook receivers as a fake: every POST is recorded and answered from a
script (2xx by default); addresses of `refused_hosts` are refused as the
SSRF guard refuses private ones. No network.
"""

from collections import deque
from urllib.parse import urlsplit

from app.contracts.integrations import WebhookPosterContract
from app.schemas.constants.integrations import WebhookDeliveryProblem
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookPostRequest,
    WebhookPostResult,
)
from app.schemas.typings.integrations.constrained_strings import (
    WebhookErrorText,
    WebhookTargetUrl,
)
from app.schemas.typings.observability.constrained_integers import HttpStatusCode

DELIVERED: WebhookPostResult = WebhookPostResult(status_code=HttpStatusCode(200))
NOT_PUBLIC: WebhookPostResult = WebhookPostResult(
    problem=WebhookDeliveryProblem.NOT_PUBLIC,
    error=WebhookErrorText("The address is not a public internet address."),
)


def answer(status: int) -> WebhookPostResult:
    if status == 410:
        return WebhookPostResult(
            status_code=HttpStatusCode(410),
            problem=WebhookDeliveryProblem.GONE,
            error=WebhookErrorText("The address answered 410 Gone."),
        )
    if 200 <= status < 300:
        return WebhookPostResult(status_code=HttpStatusCode(status))
    return WebhookPostResult(
        status_code=HttpStatusCode(status),
        problem=WebhookDeliveryProblem.HTTP_STATUS,
        error=WebhookErrorText(f"The address answered {status}."),
    )


class FakeWebhookPoster(WebhookPosterContract):
    def __init__(self) -> None:
        self.posted: list[WebhookPostRequest] = []
        self.answers: deque[WebhookPostResult] = deque()
        self.refused_hosts: set[str] = {"localhost", "10.0.0.7", "169.254.169.254"}

    def answer_next(self, *results: WebhookPostResult) -> None:
        self.answers.extend(results)

    def vet(self, url: WebhookTargetUrl) -> WebhookPostResult | None:
        host = urlsplit(str(url)).hostname or ""
        return NOT_PUBLIC if host in self.refused_hosts else None

    def post(self, request: WebhookPostRequest) -> WebhookPostResult:
        refusal = self.vet(request.url)
        if refusal is not None:
            return refusal

        self.posted.append(request)
        return self.answers.popleft() if self.answers else DELIVERED
