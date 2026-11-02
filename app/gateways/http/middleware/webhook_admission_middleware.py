"""
Admission of the providers' webhook deliveries, before their bodies are
read: a flood from one client network is refused with 429 (Retry-After)
by the provider's flood budget, and a delivery without the provider's
signature header in its exact shape is refused at once (401; Stripe's
verifier answers 403, so its refusals do too). The route's verifier then
checks the signature itself and its freshness (`webhook_deliveries`).
Nothing is read and nothing is stored for a refused
delivery; each refusal is a security log line (provider, path, client
network, reason), a flood once when it starts.
"""

import time
from collections.abc import Mapping

from starlette.types import ASGIApp, Receive, Scope, Send

from app.gateways.http.middleware.error_answers import (
    client_address_of,
    header_map,
    send_error_answer,
)
from app.gateways.http.middleware.flood_budgets import (
    BudgetDecision,
    FloodBudget,
    MonotonicClock,
    network_key,
)
from app.gateways.http.middleware.webhook_deliveries import (
    WEBHOOK_ROUTES,
    WebhookRoute,
    find_webhook_route,
)
from app.schemas.constants.errors import ApiErrorCode
from app.utilities.observability.security_events import (
    RATE_LIMIT_TRIGGERED,
    WEBHOOK_DELIVERY_REFUSED,
    log_security_event,
)

SIGNED_METHOD: str = "POST"
FLOOD_MESSAGE: str = "Too many webhook deliveries; retry later."
REFUSED_MESSAGE: str = "The webhook delivery is not signed as its provider signs."
FLOOD_REASON: str = "flood_budget"


class WebhookAdmissionMiddleware:
    """
    Pure ASGI middleware in front of the webhook routes
    (`webhook_deliveries.WEBHOOK_ROUTES`); every other request passes
    untouched.
    """

    def __init__(
        self,
        app: ASGIApp,
        clock: MonotonicClock = time.monotonic,
        per_minute: Mapping[str, int] | None = None,
    ) -> None:
        """`per_minute` overrides the budget of a provider (tests)."""

        self.app: ASGIApp = app
        overrides: Mapping[str, int] = per_minute or {}
        self._budgets: dict[WebhookRoute, FloodBudget] = {
            route: FloodBudget(
                overrides.get(route.provider, route.per_minute), clock=clock
            )
            for route in WEBHOOK_ROUTES
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        route: WebhookRoute | None = (
            find_webhook_route(str(scope.get("path", "")))
            if scope["type"] == "http"
            else None
        )
        if route is None:
            await self.app(scope, receive, send)
            return

        client_address: str | None = client_address_of(scope)
        decision: BudgetDecision = self._budgets[route].spend(
            network_key(route.provider, client_address)
        )
        if not decision.is_admitted:
            if decision.is_new_refusal:
                log_security_event(
                    RATE_LIMIT_TRIGGERED,
                    path=route.path,
                    reason=FLOOD_REASON,
                    client_address=client_address,
                    provider=route.provider,
                )
            await send_error_answer(
                send,
                429,
                ApiErrorCode.RATE_LIMITED,
                FLOOD_MESSAGE,
                {"Retry-After": str(decision.retry_after_seconds)},
            )
            return

        reason: str | None = (
            route.check(header_map(scope))
            if scope.get("method") == SIGNED_METHOD
            else None
        )
        if reason is None:
            await self.app(scope, receive, send)
            return

        log_security_event(
            WEBHOOK_DELIVERY_REFUSED,
            path=route.path,
            reason=reason,
            client_address=client_address,
            provider=route.provider,
        )
        await send_error_answer(
            send,
            route.refusal_status,
            ApiErrorCode.ACCESS_DENIED
            if route.refusal_status == 403
            else ApiErrorCode.AUTHENTICATION_REQUIRED,
            REFUSED_MESSAGE,
            {"WWW-Authenticate": "Signature"} if route.refusal_status == 401 else {},
        )
