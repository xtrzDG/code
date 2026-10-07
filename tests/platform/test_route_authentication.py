"""
Authentication of every operation outside /v1/businesses/{business_id}
(those have the authorization matrix, tests/platform/test_authorization_matrix.py),
read from the API description so a new route is covered by itself:

- without credentials, every operation answers 401 before it does anything,
  except the reviewed public ones (tests/platform/route_access_tables.py),
  each protected by a signature, a signed link or its own limits;
- the platform admin's operations refuse a business owner (403);
- the public API takes an API key only: a cabinet token is 401 there.
"""

from collections.abc import Iterator, Sequence
from typing import Any, cast

import pytest
from fastapi import APIRouter
from httpx2 import Response
from starlette.routing import BaseRoute, Mount

from app.schemas.constants.users import LoginMethod
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.client_health.prefixed_id import ClientNoteId
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.security.platform_admin_ids import derive_platform_admin_id
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.platform.authorization_requests import HTTP_METHODS, PATH_PARAMETER
from tests.platform.route_access_tables import (
    ADMIN_BODIES,
    ADMIN_PREFIX,
    ADMIN_QUERIES,
    PUBLIC_API_PREFIX,
    PUBLIC_OPERATIONS,
    UNDOCUMENTED_ROUTES,
)

BUSINESS_PREFIX: str = "/v1/businesses/{business_id}"
# Operations outside the business prefix today; fewer means routes were lost.
MINIMUM_OPERATIONS: int = 120
OWNER_PHONE: str = "+995 555 12 34 56"
PLACEHOLDER_ID: str = "missing"
# Well-formed ids of records that do not exist: malformed ones stop at the
# path parsing (404) before any authorization runs.
WELL_FORMED_IDS: dict[str, str] = {
    "admin_id": str(
        derive_platform_admin_id(LoginMethod.EMAIL, EmailAddress("a@example.com"))
    ),
    "announcement_id": str(AnnouncementId()),
    "invoice_id": str(InvoiceId()),
    "job_id": str(QueuedJobId()),
    "note_id": str(ClientNoteId()),
    "partner_id": str(PartnerId()),
    "task_key": "backfill_lookup:contacts.last_seen_at",
}

type Operation = tuple[str, str, bool]


@pytest.fixture(scope="module")
def workshop() -> Iterator[Workshop]:
    opened = start_workshop()
    with opened.client:
        yield opened


@pytest.fixture(scope="module")
def owner(workshop: Workshop) -> dict[str, str]:
    """A business owner who is no platform admin."""

    return bearer(workshop.sign_in_with_phone(OWNER_PHONE)[0])


def operations(workshop: Workshop) -> list[Operation]:
    """(method, path, has a body) of every documented non-business operation."""

    paths = cast(dict[str, dict[str, Any]], workshop.application.openapi()["paths"])
    found: list[Operation] = []
    for path, path_item in sorted(paths.items()):
        if path.startswith(BUSINESS_PREFIX):
            continue
        for method in HTTP_METHODS:
            operation: dict[str, Any] | None = path_item.get(method)
            if operation is not None:
                found.append((method.upper(), path, "requestBody" in operation))
    return found


def call(
    workshop: Workshop,
    operation: Operation,
    headers: dict[str, str],
    ids: dict[str, str] | None = None,
) -> Response:
    """The operation with `ids` in its path (others a placeholder), a body."""

    method, path, has_body = operation
    values: dict[str, str] = ids or {}
    return workshop.client.request(
        method,
        PATH_PARAMETER.sub(
            lambda match: values.get(match.group(1), PLACEHOLDER_ID), path
        ),
        params=ADMIN_QUERIES.get(key(operation)),
        json=ADMIN_BODIES.get(key(operation), {}) if has_body else None,
        headers=headers,
    )


def refusal(response: Response, status_code: int, error_code: str) -> str | None:
    body: object = response.json() if response.content else None
    code: object = (
        cast(dict[str, object], body).get("error") if isinstance(body, dict) else None
    )
    if response.status_code == status_code and code == error_code:
        return None
    return f"got {response.status_code} {response.text[:120]}"


def key(operation: Operation) -> str:
    return f"{operation[0]} {operation[1]}"


def route_paths(routes: Sequence[BaseRoute], prefix: str = "") -> Iterator[str]:
    """Every route's full path, through included routers and mounts."""

    for route in routes:
        # FastAPI keeps an included router whole, with its include prefix.
        included: object = getattr(route, "original_router", None)
        context: object = getattr(route, "include_context", None)
        if isinstance(included, APIRouter):
            yield from route_paths(
                included.routes, prefix + str(getattr(context, "prefix", ""))
            )
        elif isinstance(route, Mount):
            yield from route_paths(route.routes, prefix + route.path)
        else:
            yield prefix + str(getattr(route, "path", ""))


def test_the_public_list_names_only_existing_operations(workshop: Workshop) -> None:
    keys = {key(operation) for operation in operations(workshop)}

    assert len(keys) >= MINIMUM_OPERATIONS
    assert sorted(set(PUBLIC_OPERATIONS) - keys) == []


def test_routes_left_out_of_the_description_are_the_reviewed_ones(
    workshop: Workshop,
) -> None:
    documented = set(cast(dict[str, Any], workshop.application.openapi()["paths"]))
    hidden = set(route_paths(workshop.application.routes)) - documented

    # A new route outside the description must be reviewed and listed.
    assert sorted(hidden) == sorted(UNDOCUMENTED_ROUTES)


def test_every_other_operation_refuses_a_caller_without_credentials(
    workshop: Workshop,
) -> None:
    failures: list[str] = []
    for operation in operations(workshop):
        if key(operation) in PUBLIC_OPERATIONS:
            continue
        problem = refusal(call(workshop, operation, {}), 401, "authentication_required")
        if problem is not None:
            failures.append(f"{key(operation)}: {problem}")

    assert failures == []


def test_admin_operations_refuse_a_business_owner(
    workshop: Workshop, owner: dict[str, str]
) -> None:
    created = workshop.client.post(
        "/v1/businesses",
        json={"name": "Salobie", "niche_key": "restaurant"},
        headers=owner,
    )
    assert created.status_code == 201, created.text
    # Even about their own business, an owner opens no admin page.
    ids = {**WELL_FORMED_IDS, "business_id": str(created.json()["id"])}
    failures: list[str] = []
    for operation in operations(workshop):
        if not operation[1].startswith(ADMIN_PREFIX):
            continue
        response = call(workshop, operation, owner, ids)
        problem = refusal(response, 403, "access_denied")
        if problem is not None:
            failures.append(f"{key(operation)}: {problem}")

    assert failures == []


def test_the_public_api_refuses_a_cabinet_token(
    workshop: Workshop, owner: dict[str, str]
) -> None:
    public_api = [
        operation
        for operation in operations(workshop)
        if operation[1].startswith(PUBLIC_API_PREFIX)
    ]
    failures = [
        f"{key(operation)}: {problem}"
        for operation in public_api
        if (
            problem := refusal(
                call(workshop, operation, owner), 401, "authentication_required"
            )
        )
        is not None
    ]

    assert len(public_api) >= 13
    assert failures == []
