"""
The generic per-address limit of requests without a verified credential
(API_REQUESTS_PER_IP_PER_MINUTE): a 429 with Retry-After before the route
runs. Signed-in requests count per person in the credential dependency
instead (`user_authentication`, `api_key_authentication`), which counts a
refused token against its address like a missing one.

An Authorization header alone exempts nothing. A request without one is
counted before routing; one with a header is counted once its route is
known (`admit_anonymous_request`, a dependency of every route), unless that
route checks the credential itself (`verifies_credential`). A header on a
path no route serves is counted after its 404. Routes with limits of their
own or callers that are not browsers are left alone: the website chat
(per visitor, network, business and platform), the providers' webhooks
(their admission budgets, `webhook_admission_middleware`), the landing
page's demos, the widget script, health checks and the API description.
"""

from collections.abc import Callable, Iterable

from fastapi import Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Receive, Scope, Send

from app.gateways.http.middleware.error_answers import (
    client_address_of,
    send_error_answer,
)
from app.gateways.http.middleware.flood_budgets import is_first_line_this_minute
from app.schemas.constants.errors import ApiErrorCode
from app.schemas.dto.spend_guard import ApiRequestAdmission
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.utilities.observability.security_events import (
    RATE_LIMIT_TRIGGERED,
    log_security_event,
)

type AdmitRequest = Callable[[ApiRequestAdmission], None]

# Set on a dependency that checks the request's credential and counts a
# refused one against the caller's address.
CREDENTIAL_CHECK_ATTRIBUTE: str = "verifies_credential"
# The request state of a request with a header whose count waits for its
# route: the admission to call, and whether it was decided.
DEFERRED_ADMISSION_STATE: str = "workshop_deferred_admission"
ADMISSION_DECIDED_STATE: str = "workshop_admission_decided"
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
    """Counts each request without a verified credential against its address."""

    def __init__(self, app: ASGIApp, admit: AdmitRequest) -> None:
        self.app: ASGIApp = app
        self._admit: AdmitRequest = admit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        client_address: str | None = client_address_of(scope)
        if scope["type"] != "http" or client_address is None or is_exempt(scope):
            await self.app(scope, receive, send)
            return

        if carries_authorization(scope):
            state: dict[str, object] = scope.setdefault("state", {})
            state[DEFERRED_ADMISSION_STATE] = self._admit
            await self.app(scope, receive, send)
            if not state.get(ADMISSION_DECIDED_STATE):
                # No route took the request (404, 405): it counts all the same.
                await count_quietly(self._admit, client_address)
            return

        try:
            await admit_address(self._admit, client_address)
        except RateLimitedError as error:
            label: str = str(scope.get("method", "")) + " " + path_label(scope)
            if is_first_line_this_minute(f"{label}:{client_address}"):
                log_security_event(
                    RATE_LIMIT_TRIGGERED,
                    path=label,
                    reason=ANONYMOUS_LIMIT_REASON,
                    client_address=client_address,
                )
            await send_too_many_requests(send, error)
            return

        await self.app(scope, receive, send)


async def admit_anonymous_request(request: Request) -> None:
    """
    The dependency of every route that counts a request with an
    Authorization header against its address, unless the route checks
    that credential itself (then a refused one is counted there).
    """

    state: dict[str, object] = request.scope.setdefault("state", {})
    admit: object = state.pop(DEFERRED_ADMISSION_STATE, None)
    if not callable(admit):
        return

    state[ADMISSION_DECIDED_STATE] = True
    route: object = request.scope.get("route")
    if isinstance(route, APIRoute) and route_checks_credential(route):
        return

    client_address: str | None = client_address_of(request.scope)
    if client_address is not None:
        # A refusal is a RateLimitedError: the error handler answers (and
        # logs) it like any other 429.
        await admit_address(admit, client_address)


def route_checks_credential(route: APIRoute) -> bool:
    known: object = getattr(route, CREDENTIAL_CHECK_ATTRIBUTE, None)
    if isinstance(known, bool):
        return known

    found: bool = checks_credential(route.dependant)
    setattr(route, CREDENTIAL_CHECK_ATTRIBUTE, found)
    return found


async def admit_address(admit: object, client_address: str) -> None:
    """Count one request of the address; RateLimitedError past its limit."""

    if callable(admit):
        await run_in_threadpool(
            admit,
            ApiRequestAdmission(client_ip_address=ClientIpAddress(client_address)),
        )


async def count_quietly(admit: AdmitRequest, client_address: str) -> None:
    try:
        await admit_address(admit, client_address)
    except RateLimitedError:
        return


def path_label(scope: Scope) -> str:
    """The first two segments of the path (no ids in a security log)."""

    return "/" + "/".join(str(scope.get("path", "")).split("/")[1:3])


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
