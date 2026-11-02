"""
The cabinet's own HTTP entry points: the route handlers of the Next.js app
(`web/src/app/**/route.ts`). Pages only render; what they change goes
through the proxy `/api/backend/*` to the API. A new route handler fails
the inventory until it is classified here.
"""

import re
from pathlib import Path

from scripts.entry_points.access_classes import (
    ACCOUNT,
    AS_API,
    OWNER,
    PUBLIC,
    HttpEntryPoint,
)

ROOT: Path = Path(__file__).resolve().parents[2]
CABINET_APP: Path = ROOT / "web" / "src" / "app"
# `export async function POST(` or `export { forward as GET, ... }`.
METHOD_EXPORTS: tuple[re.Pattern[str], ...] = (
    re.compile(r"export (?:async )?(?:function|const) (GET|POST|PUT|PATCH|DELETE)\b"),
    re.compile(r"\bforward as (GET|POST|PUT|PATCH|DELETE)\b"),
)
SIGN_IN_STEP: str = "a sign-in step, forwarded to the API's operation and its limits"
# The route of each handler (folder path, route groups dropped): its access
# class, scope and protection.
CABINET_ROUTES: dict[str, tuple[str, str, str]] = {
    "/.well-known/security.txt": (PUBLIC, "none", "published contacts (RFC 9116)"),
    "/api/auth/expired": (
        PUBLIC,
        "none",
        "drops the cookie only when the API rejects the session now",
    ),
    "/api/auth/logout": (ACCOUNT, "own account", "the session cookie"),
    "/api/auth/mfa/enroll": (PUBLIC, "none", SIGN_IN_STEP),
    "/api/auth/mfa/passkey/enroll": (PUBLIC, "none", SIGN_IN_STEP),
    "/api/auth/mfa/passkey/enroll/finish": (PUBLIC, "none", SIGN_IN_STEP),
    "/api/auth/mfa/passkey/options": (PUBLIC, "none", SIGN_IN_STEP),
    "/api/auth/mfa/passkey/verify": (PUBLIC, "none", SIGN_IN_STEP),
    "/api/auth/mfa/verify": (PUBLIC, "none", SIGN_IN_STEP),
    "/api/auth/start": (PUBLIC, "none", SIGN_IN_STEP),
    "/api/auth/verify": (PUBLIC, "none", SIGN_IN_STEP),
    "/api/backend/[...path]": (
        AS_API,
        "as the API operation",
        "the session cookie becomes the bearer token; only /v1/* is forwarded",
    ),
    "/api/consent": (
        PUBLIC,
        "none",
        "the visitor's own cookie choice; same-origin only, 4 KB",
    ),
    "/api/csp-report": (
        PUBLIC,
        "none",
        "browser reports: type and size checked, counted, cleaned",
    ),
    "/api/locale": (
        PUBLIC,
        "none",
        "the interface language; same-origin only, 1 KB",
    ),
    "/api/monitoring": (
        PUBLIC,
        "none",
        "the error tunnel: same-origin pages only, size and rate capped",
    ),
    "/integrations/google-calendar/callback": (
        OWNER,
        "business",
        "the session of the owner who started connecting",
    ),
}


class UnclassifiedRouteError(ValueError):
    """A route handler of the cabinet that CABINET_ROUTES does not name."""


def route_path(handler: Path, app_directory: Path) -> str:
    """`/api/auth/start` of `.../app/api/auth/start/route.ts`."""

    parts: list[str] = [
        part
        for part in handler.parent.relative_to(app_directory).parts
        if not (part.startswith("(") and part.endswith(")"))
    ]
    return "/" + "/".join(parts)


def handler_methods(handler: Path) -> list[str]:
    source: str = handler.read_text(encoding="utf-8")
    return sorted({m for pattern in METHOD_EXPORTS for m in pattern.findall(source)})


def cabinet_entry_points(app_directory: Path = CABINET_APP) -> list[HttpEntryPoint]:
    """
    Raises:
        UnclassifiedRouteError: a route handler CABINET_ROUTES does not name.
    """

    found: list[HttpEntryPoint] = []
    for handler in sorted(app_directory.rglob("route.ts")):
        path: str = route_path(handler, app_directory)
        if path not in CABINET_ROUTES:
            raise UnclassifiedRouteError(
                f"{handler} is not classified: add {path!r} to CABINET_ROUTES "
                "in scripts/entry_points/cabinet_routes.py"
            )
        access, scope, protected_by = CABINET_ROUTES[path]
        found.extend(
            HttpEntryPoint(method, path, access, scope, protected_by)
            for method in handler_methods(handler)
        )
    return sorted(found, key=lambda entry: entry.key)
