"""
The generic per-address limit of requests without a verified credential
(API_REQUESTS_PER_IP_PER_MINUTE): a 429 with Retry-After before any route
runs. Signed-in requests count per person in the credential dependency
instead (`user_authentication`, `api_key_authentication`), which counts a
refused token against its address like a missing one.

An Authorization header alone exempts nothing: a request is left to its
credential dependency only when the route it goes to checks a credential
(`verifies_credential`); a made-up header on any other route counts here
as no header does. Routes with limits of their own or callers that are
not browsers are left alone: the website chat (per visitor, network,
business and platform), the providers' webhooks (their admission budgets,
`webhook_admission_middleware`), the landing page's demos, the widget
script, health checks and the API description.
"""

from collections.abc import Callable, Iterable, Sequence

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.routing import BaseRoute, Match
from starlette.types import ASGIApp, Receive, Scope, Send

from app.gateways.http.middleware.error_answers import (
    client_address_of,
    send_error_answer,
)
from app.schemas.constants.errors import ApiErrorCode
from app.schemas.dto.spend_guard import ApiRequestAdmission
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.utilities.observability.security_events import (
    RATE_LIMIT_TRIGGERED,
    log_security_event,
)

type AdmitRequest = Callable[[ApiRequestAdmission], None]
type RoutesSource = Callable[[], Sequence[BaseRoute]]

# Set on a dependency that checks the request's credential and counts a
# refused one against the caller's address.
CREDENTIAL_CHECK_ATTRIBUTE: str = "verifies_credential"
EXEMPT_PREFIXES: tuple[str, ...] = (
    "/healthz",
    "/readyz",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/widget",
    "/v1/widget/",
    "/v1/channels/",
    "/v1/voice/",
    "/v1/telephony/",
    "/v1/payments/",
    "/v1/public-demos",
)
ANONYMOUS_LIMIT_REASON: str = "anonymous_address_limit"


def mark_credential_check[Dependency: Callable[..., object]](
    dependency: Dependency,
) -> Dependency:
    """Mark a dependency as one that checks (and counts) a credential."""

    setattr(dependency, CREDENTIAL_CHECK_ATTRIBUTE, True)
    return dependency


def is_exempt(scope: Scope) -> bool:
    """Routes with limits of their own and preflights."""

    path: str = str(scope.get("path", ""))
    return scope.get("method") == "OPTIONS" or path.startswith(EXEMPT_PREFIXES)


def carries_authorization(scope: Scope) -> bool:
    headers: Iterable[tuple[bytes, bytes]] = scope.get("headers", [])
    return any(name.lower() == b"authorization" for name, _ in headers)


def checks_credential(dependant: Dependant) -> bool:
    """Whether the dependency tree of a route checks a credential."""

    if getattr(dependant.call, CREDENTIAL_CHECK_ATTRIBUTE, False):
        return True

    return any(checks_credential(child) for child in dependant.dependencies)


class AnonymousRequestLimitMiddleware:
    """Counts each request without a verified credential against its network."""

    def __init__(
        self,
        app: ASGIApp,
        admit: AdmitRequest,
        routes: RoutesSource | None = None,
    ) -> None:
        self.app: ASGIApp = app
        self._admit: AdmitRequest = admit
        self._routes: RoutesSource | None = routes
        self._credential_routes: list[APIRoute] | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        client_address: str | None = client_address_of(scope)
        if (
            scope["type"] != "http"
            or client_address is None
            or is_exempt(scope)
            or (carries_authorization(scope) and self._checks_credential(scope))
        ):
            await self.app(scope, receive, send)
            return

        admission = ApiRequestAdmission(
            client_ip_address=ClientIpAddress(client_address)
        )
        try:
            await run_in_threadpool(self._admit, admission)
        except RateLimitedError as error:
            log_security_event(
                RATE_LIMIT_TRIGGERED,
                path=str(scope.get("method", "")) + " " + route_label(scope),
                reason=ANONYMOUS_LIMIT_REASON,
                client_address=client_address,
            )
            await send_too_many_requests(send, error)
            return

        await self.app(scope, receive, send)

    def _checks_credential(self, scope: Scope) -> bool:
        """Whether the route the request goes to checks its credential."""

        if self._credential_routes is None:
            routes: Sequence[BaseRoute] = [] if self._routes is None else self._routes()
            self._credential_routes = [
                route
                for route in routes
                if isinstance(route, APIRoute) and checks_credential(route.dependant)
            ]

        return any(
            route.matches(scope)[0] is Match.FULL for route in self._credential_routes
        )


def route_label(scope: Scope) -> str:
    """The first two segments of the path (no ids in a security log)."""

    segments: list[str] = str(scope.get("path", "")).split("/")[1:3]
    return "/" + "/".join(segments)


async def send_too_many_requests(send: Send, error: RateLimitedError) -> None:
    await send_error_answer(
        send,
        429,
        ApiErrorCode.RATE_LIMITED,
        str(error),
        (
            {}
            if error.retry_after_seconds is None
            else {"Retry-After": str(int(error.retry_after_seconds))}
        ),
    )
