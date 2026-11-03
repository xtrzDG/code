"""
The public API's cross-tenant matrix (AUTHZ-02), generated from the
application's own OpenAPI description, so a new operation is in it by
itself: every /v1/public-api operation is called with a key of business A
(every scope), each path id naming a record of business B and each body
naming B's records wherever it can. Every answer is a refusal (403 or 404;
a body naming B's record may also be 409 or 422) or A's own data, and none
holds an id or a name of B; B's records are unchanged afterwards. A path
parameter or a request body the matrix has no record of B for fails the
test until the matrix names one (tenant_matrix_records.py).
"""

import re
from typing import Any

from httpx2 import Response

from tests.integrations.integration_shop import (
    IntegrationShop,
    open_integration_shop,
    open_other_business,
)
from tests.integrations.tenant_matrix_records import (
    THEIR_CONTACT_NAME,
    TheirRecords,
    make_their_records,
)

PUBLIC_API_PREFIX: str = "/v1/public-api"
HTTP_METHODS: frozenset[str] = frozenset({"get", "post", "put", "patch", "delete"})
PARAMETER: re.Pattern[str] = re.compile(r"{([a-z_]+)}")
REFUSALS: frozenset[int] = frozenset({403, 404})
BODY_REFUSALS: frozenset[int] = frozenset({403, 404, 409, 422})
# Bodies that name one of B's records: they must be refused.
BODIES_NAMING_THEIRS: frozenset[tuple[str, str]] = frozenset(
    {("POST", "/v1/public-api/bookings")}
)

type Operation = tuple[str, str]


def public_api_operations(shop: IntegrationShop) -> dict[Operation, dict[str, Any]]:
    paths: dict[str, dict[str, Any]] = shop.workshop.application.openapi()["paths"]
    return {
        (method.upper(), path): operation
        for path, item in paths.items()
        if path.startswith(PUBLIC_API_PREFIX)
        for method, operation in item.items()
        if method in HTTP_METHODS
    }


def call(
    shop: IntegrationShop,
    key: str,
    theirs: TheirRecords,
    operation: Operation,
    description: dict[str, Any],
) -> Response:
    method, path = operation
    ids: dict[str, str] = theirs.path_ids()
    for parameter in PARAMETER.findall(path):
        assert parameter in ids, (
            f"{method} {path}: no record of another business for {{{parameter}}}; "
            "name one in tenant_matrix_records.TheirRecords.path_ids"
        )
        path = path.replace(f"{{{parameter}}}", ids[parameter])

    body: dict[str, Any] | None = None
    if "requestBody" in description:
        assert operation in theirs.bodies(), (
            f"{method} {path}: a request body the matrix does not know; add one "
            "to tenant_matrix_records.TheirRecords.bodies"
        )
        body = theirs.bodies()[operation]

    return shop.api(method, path.removeprefix(PUBLIC_API_PREFIX), key, body)


def leaked(theirs: TheirRecords, response: Response) -> list[str]:
    """B's ids and names in the answer, beyond the ones the request named."""

    sent: str = f"{response.request.url} {response.request.content.decode()}"
    return [
        marker
        for marker in (*theirs.markers(), THEIR_CONTACT_NAME)
        if marker in response.text and marker not in sent
    ]


def test_every_public_api_operation_keeps_to_the_keys_business() -> None:
    with open_integration_shop() as shop:
        their_shop = open_other_business(shop.workshop)
        theirs = make_their_records(their_shop)
        shop.book()
        key = shop.add_api_key()
        operations = public_api_operations(shop)
        answers: dict[Operation, Response] = {
            operation: call(shop, key, theirs, operation, description)
            for operation, description in sorted(operations.items())
        }
        their_booking = their_shop.api(
            "GET", f"/bookings/{theirs.booking_id}", theirs.key
        )
        their_webhooks = their_shop.get(f"{their_shop.base}/webhooks")

    assert len(operations) >= 14
    for (method, path), response in answers.items():
        label = f"{method} {path}: {response.status_code} {response.text[:200]}"
        assert leaked(theirs, response) == [], label
        if PARAMETER.search(path):
            assert response.status_code in REFUSALS, label
        elif (method, path) in BODIES_NAMING_THEIRS:
            assert response.status_code in BODY_REFUSALS, label
        else:
            assert response.status_code < 300, label

    assert their_booking.status_code == 200, their_booking.text
    assert their_booking.json()["status"] != "cancelled"
    assert theirs.webhook_id in {
        str(endpoint["id"]) for endpoint in their_webhooks.json()["items"]
    }
