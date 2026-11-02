"""
Security log lines of the refusals the error handlers answer: a webhook
delivery a provider's verifier refused (also counted for the
`webhook_signature_failures` alert), a request without valid credentials
(401) or rights (403), and a rate limit that triggered (429, one line per
route and client network a minute, not one per request).
"""

from fastapi import Request
from fastapi.routing import APIRoute

from app.gateways.failure_signals import FailureSignals, failure_signals_of
from app.gateways.http.middleware.flood_budgets import is_first_line_this_minute
from app.gateways.http.middleware.webhook_deliveries import (
    WebhookRoute,
    find_webhook_route,
)
from app.schemas.constants.monitoring import PlatformSignal
from app.utilities.observability.security_events import (
    AUTHORIZATION_DENIED,
    RATE_LIMIT_TRIGGERED,
    WEBHOOK_DELIVERY_REFUSED,
    log_security_event,
)

UNAUTHORIZED: int = 401
FORBIDDEN: int = 403
TOO_MANY_REQUESTS: int = 429
CLIENT_ERROR: int = 400
SERVER_ERROR: int = 500
UNMATCHED_ROUTE: str = "unmatched"


def log_refusal(request: Request, status: int, error_code: str) -> None:
    """The security line of an error answer, when it is one worth a line."""

    client_address: str | None = None if request.client is None else request.client.host
    webhook: WebhookRoute | None = find_webhook_route(request.url.path)
    if webhook is not None and CLIENT_ERROR <= status < SERVER_ERROR:
        signals: FailureSignals | None = failure_signals_of(request.app)
        if signals is not None:
            signals.count(PlatformSignal.WEBHOOK_REFUSED)
        log_security_event(
            WEBHOOK_DELIVERY_REFUSED,
            path=webhook.path,
            reason=error_code,
            client_address=client_address,
            provider=webhook.provider,
            status=status,
        )
        return

    path: str = request.method + " " + route_template(request)
    if status in (UNAUTHORIZED, FORBIDDEN):
        log_security_event(
            AUTHORIZATION_DENIED,
            path=path,
            reason=error_code,
            client_address=client_address,
            status=status,
        )
    elif status == TOO_MANY_REQUESTS and is_first_line_this_minute(
        f"{path}:{client_address}"
    ):
        log_security_event(
            RATE_LIMIT_TRIGGERED,
            path=path,
            reason=error_code,
            client_address=client_address,
            status=status,
        )


def route_template(request: Request) -> str:
    """The template of the route that answered (no ids in a log line)."""

    route: object = request.scope.get("route")
    return route.path if isinstance(route, APIRoute) else UNMATCHED_ROUTE
