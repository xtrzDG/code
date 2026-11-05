"""
The backend's HTTP routes with their access class, read from the live
application and the reviewed tables of the route tests:

- `tests/platform/route_access_tables.py`: what answers without a token or
  an API key, and what protects it instead (proven by
  `tests/platform/test_route_authentication.py`);
- `tests/platform/authorization_tables.py`: a business's owner-only
  operations (proven by `tests/platform/test_authorization_matrix.py`);
- `tests/platform/brand_matrix_checks.py`: a brand's owner-only operations
  (proven by `tests/platform/test_brand_authorization_matrix.py`).

This module only reads those tables; the tests decide whether they hold.
An operation none of them classifies (and outside `ACCOUNT_PREFIXES`)
stops the inventory instead of getting a class by default.
"""

from collections.abc import Iterator, Sequence

from fastapi import APIRouter, FastAPI
from starlette.routing import BaseRoute, Mount

from scripts.entry_points.access_classes import (
    ACCOUNT,
    API_KEY,
    CUSTOMER,
    OPERATOR_TOKEN,
    OWNER,
    PLATFORM_ADMIN,
    PUBLIC,
    SIGNED_WEBHOOK,
    STAFF,
    HttpEntryPoint,
    UnclassifiedRouteError,
)
from tests.platform.authorization_tables import OWNER_ONLY_OPERATIONS
from tests.platform.brand_matrix_checks import BRAND_OWNER_ONLY
from tests.platform.route_access_tables import (
    ADMIN_PREFIX,
    PUBLIC_API_PREFIX,
    PUBLIC_OPERATIONS,
    UNDOCUMENTED_ROUTES,
)

BUSINESS_PREFIX: str = "/v1/businesses/{business_id}"
BRAND_PREFIX: str = "/v1/brands/{brand_id}"
# Public operations under these prefixes are providers' callbacks...
WEBHOOK_PREFIXES: tuple[str, ...] = (
    "/v1/channels/",
    "/v1/voice/",
    "/v1/payments/",
    "/v1/telephony/",
)
# ... and these a business's customers' (chat, signed links).
CUSTOMER_PREFIXES: tuple[str, ...] = ("/v1/public/", "/v1/widget/{business_id}/")
# The website chat's CORS preflights; an OPTIONS route anywhere else is
# classified like any other operation.
PREFLIGHT_PREFIX: str = "/v1/widget/"
# Operations outside the business prefix that act for one business's owner.
OWNER_OPERATIONS_ELSEWHERE: dict[str, str] = {
    "GET /v1/business-exports/{business_id}/{export_id}/download": (
        "the one-time link of the owner who asked, with that owner's session"
    ),
    "POST /v1/integrations/google-calendar/complete": (
        "the session of the owner who started connecting (signed OAuth state)"
    ),
}
# A signed-in person's own account: these prefixes, and the two lists of
# their businesses and brands (creating one included). Anything else
# outside the tables above is unclassified, never "account" by default.
ACCOUNT_PREFIXES: tuple[str, ...] = (
    "/v1/assistants",
    "/v1/auth",
    "/v1/me",
    "/v1/partner",
    "/v1/telemetry",
)
ACCOUNT_PATHS: frozenset[str] = frozenset({"/v1/brands", "/v1/businesses"})
NOT_IN_PRODUCTION: str = "not served in production"
PREFLIGHT: str = "CORS preflight of the website chat: no data"
SESSION: str = "cabinet session token"
MEMBER_SESSION: str = "cabinet session token of a member of the business"
BRAND_SESSION: str = "cabinet session token of a member of the brand's team"
ADMIN_SESSION: str = (
    "cabinet session token with two factors and the admin role's permission"
)
METHOD_ORDER: tuple[str, ...] = (
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
)


def route_methods(
    routes: Sequence[BaseRoute], prefix: str = ""
) -> Iterator[tuple[str, str]]:
    """(method, full path) of every route, through included routers and mounts."""

    for route in routes:
        # FastAPI keeps an included router whole, with its include prefix.
        included: object = getattr(route, "original_router", None)
        context: object = getattr(route, "include_context", None)
        if isinstance(included, APIRouter):
            yield from route_methods(
                included.routes, prefix + str(getattr(context, "prefix", ""))
            )
        elif isinstance(route, Mount):
            yield from route_methods(route.routes, prefix + route.path)
        else:
            path: str = prefix + str(getattr(route, "path", ""))
            methods: set[str] = set(getattr(route, "methods", None) or ())
            for method in methods - {"HEAD"} or methods:
                yield method, path


def is_under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def classify_open(method: str, path: str) -> HttpEntryPoint | None:
    """An entry point the reviewed tables let answer without a token."""

    key: str = f"{method} {path}"
    if method == "OPTIONS" and path.startswith(PREFLIGHT_PREFIX):
        return HttpEntryPoint(method, path, PUBLIC, "none", PREFLIGHT)

    if key in PUBLIC_OPERATIONS:
        reason: str = PUBLIC_OPERATIONS[key]
        if path.startswith(WEBHOOK_PREFIXES):
            return HttpEntryPoint(method, path, SIGNED_WEBHOOK, "provider", reason)
        if path.startswith(CUSTOMER_PREFIXES):
            return HttpEntryPoint(method, path, CUSTOMER, "customer", reason)
        return HttpEntryPoint(method, path, PUBLIC, "none", reason)

    if path in UNDOCUMENTED_ROUTES:
        hidden: str = UNDOCUMENTED_ROUTES[path]
        access: str = OPERATOR_TOKEN if "METRICS_TOKEN" in hidden else PUBLIC
        served: bool = NOT_IN_PRODUCTION not in hidden
        return HttpEntryPoint(method, path, access, "platform", hidden, served)

    return None


def classify(method: str, path: str) -> HttpEntryPoint:
    """
    The access class of one operation of the API.

    Raises:
        UnclassifiedRouteError: an operation no reviewed table classifies.
    """

    key: str = f"{method} {path}"
    opened: HttpEntryPoint | None = classify_open(method, path)
    if opened is not None:
        return opened

    if key in OWNER_OPERATIONS_ELSEWHERE:
        reason: str = OWNER_OPERATIONS_ELSEWHERE[key]
        return HttpEntryPoint(method, path, OWNER, "business", reason)
    if path.startswith(ADMIN_PREFIX):
        return HttpEntryPoint(method, path, PLATFORM_ADMIN, "platform", ADMIN_SESSION)
    if path.startswith(PUBLIC_API_PREFIX):
        return HttpEntryPoint(method, path, API_KEY, "business", "the API key")
    if is_under(path, BUSINESS_PREFIX):
        role: str = OWNER if key in OWNER_ONLY_OPERATIONS else STAFF
        return HttpEntryPoint(method, path, role, "business", MEMBER_SESSION)
    if is_under(path, BRAND_PREFIX):
        role = OWNER if key in BRAND_OWNER_ONLY else STAFF
        return HttpEntryPoint(method, path, role, "brand", BRAND_SESSION)
    if path in ACCOUNT_PATHS or any(is_under(path, p) for p in ACCOUNT_PREFIXES):
        return HttpEntryPoint(method, path, ACCOUNT, "own account", SESSION)
    raise UnclassifiedRouteError(
        f"{key} is not classified: give it an access class in "
        "scripts/entry_points/api_routes.py (ACCOUNT_PREFIXES for a person's "
        "own account) or in the reviewed tables of tests/platform/"
    )


def api_entry_points(application: FastAPI) -> list[HttpEntryPoint]:
    """Every operation of the API with its access class, in path order."""

    found: set[tuple[str, str]] = set(route_methods(application.routes))
    return sorted(
        (classify(method, path) for method, path in found),
        key=lambda entry: (entry.path, METHOD_ORDER.index(entry.method)),
    )
