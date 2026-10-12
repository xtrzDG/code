"""
The checks of the brand authorization matrix, shared by the in-memory run
(tests/platform/test_brand_authorization_matrix.py) and the Postgres run
with row-level security (tests/storage/test_brand_authorization_matrix_
postgres.py): every operation under /v1/brands/{brand_id}, read from the
API description, against strangers, a regional manager and the owners.
"""

from typing import Any, cast

from fastapi import FastAPI
from httpx2 import Response

from app.schemas.constants.storage import StorageScopeKind
from app.schemas.typings.brands.prefixed_id import BrandId
from tests.platform.authorization_checks import Expectation
from tests.platform.authorization_requests import (
    HTTP_METHODS,
    PATH_PARAMETER,
    MatrixOperation,
)
from tests.platform.authorization_world import Headers
from tests.platform.brand_matrix_world import BrandWorld
from tests.platform.storage_snapshot import (
    StorageSnapshot,
    describe_changes,
    take_storage_snapshot,
)

type JsonObject = dict[str, Any]

BR: str = "/v1/brands/{brand_id}"
# What a regional manager may not do (403): everything but reading.
BRAND_OWNER_ONLY: frozenset[str] = frozenset(
    {
        f"PATCH {BR}",
        f"DELETE {BR}",
        f"POST {BR}/locations",
        f"DELETE {BR}/locations/{{business_id}}",
        f"POST {BR}/locations/clone",
        f"POST {BR}/members",
        f"PATCH {BR}/members/{{user_id}}",
        f"DELETE {BR}/members/{{user_id}}",
        f"POST {BR}/knowledge",
        f"PUT {BR}/knowledge/{{shared_key}}",
        f"DELETE {BR}/knowledge/{{shared_key}}",
    }
)


def brand_operations(application: FastAPI) -> list[MatrixOperation]:
    """Every documented operation under /v1/brands/{brand_id}."""

    paths = cast(dict[str, JsonObject], application.openapi()["paths"])
    return [
        MatrixOperation(
            method=method, path=path, has_body="requestBody" in path_item[method]
        )
        for path, path_item in sorted(paths.items())
        if path.startswith(BR)
        for method in HTTP_METHODS
        if method in path_item
    ]


def brand_bodies(brand: BrandWorld) -> dict[str, JsonObject]:
    return {
        f"PATCH {BR}": {"name": "Mtsvane Ezo Group"},
        f"POST {BR}/locations": {"business_id": brand.outside_d},
        f"POST {BR}/locations/clone": {
            "source_business_id": brand.world.business_b,
            "name": "Mtsvane Ezo Saburtalo",
        },
        f"POST {BR}/members": {
            "email": "matrix.manager@example.com",
            "role": "regional_manager",
            "business_ids": [brand.location_c],
        },
        f"PATCH {BR}/members/{{user_id}}": {
            "role": "regional_manager",
            "business_ids": [brand.location_c],
        },
        f"POST {BR}/knowledge": {"kind": "faq", "title": "Wi-Fi", "shared_key": "wifi"},
        f"PUT {BR}/knowledge/{{shared_key}}": {"kind": "faq", "title": "Parking"},
    }


def call_brand(
    brand: BrandWorld, operation: MatrixOperation, headers: Headers
) -> Response:
    path: str = PATH_PARAMETER.sub(
        lambda match: brand.path_values[match.group(1)], operation.path
    )
    body: JsonObject | None = (
        brand_bodies(brand).get(operation.key, {}) if operation.has_body else None
    )
    return brand.world.workshop.client.request(
        operation.method.upper(), path, json=body, headers=headers
    )


def snapshot(brand: BrandWorld) -> StorageSnapshot:
    """Every document, the brands and their shared knowledge included."""

    container = brand.world.workshop.container
    scope = brand.world.storage_scope
    taken: StorageSnapshot = take_storage_snapshot(container, scope)
    with scope.platform_wide():
        for name in ("brand_collection", "brand_knowledge_item_collection"):
            collection = getattr(container.brand_collections, name)()
            taken[name] = sorted(
                document.model_dump_json() for document in collection.list_all()
            )

    return taken


def check_brand_refusals(
    brand: BrandWorld,
    headers: Headers,
    expectation: Expectation,
    only: frozenset[str] | None = None,
) -> list[str]:
    """Refused as expected, in no storage scope at all, the store unchanged."""

    operations = brand_operations(brand.world.workshop.application)
    before: StorageSnapshot = snapshot(brand)
    failures: list[str] = []
    for operation in operations:
        if only is not None and operation.key not in only:
            continue

        brand.world.storage_scope.entered.clear()
        response = call_brand(brand, operation, headers)
        entered = list(brand.world.storage_scope.entered)
        problem: str | None = expectation(response) or (
            f"entered {[(item.kind.value, item.business_id) for item in entered]}"
            if entered
            else None
        )
        if problem is not None:
            failures.append(f"{operation.key}: {problem}")

    changes = describe_changes(before, snapshot(brand))
    return failures + [f"refused requests changed the store: {c}" for c in changes]


def brand_locations(brand: BrandWorld) -> set[str]:
    container = brand.world.workshop.container
    with brand.world.storage_scope.platform_wide():
        return {
            str(business.id)
            for business in container.repositories.business_repo().list_by_brand(
                BrandId(brand.brand_id)
            )
        }


def check_members_reach_only_their_locations(brand: BrandWorld) -> list[str]:
    """
    The regional manager reads the brand (200) touching only location C;
    the owner may use every operation (the changes after the reads, the
    brand's removal last), touching only the brand's locations, never the
    whole platform.
    """

    operations = sorted(
        brand_operations(brand.world.workshop.application),
        key=lambda item: (item.method != "get", item.key == f"DELETE {BR}"),
    )
    manager_runs: list[tuple[Headers, MatrixOperation, set[str] | None]] = [
        (brand.manager, operation, {brand.location_c})
        for operation in operations
        if operation.key not in BRAND_OWNER_ONLY
    ]
    owner_runs: list[tuple[Headers, MatrixOperation, set[str] | None]] = [
        (brand.world.owner_b, operation, None) for operation in operations
    ]
    runs = manager_runs + owner_runs
    failures: list[str] = []
    for headers, operation, allowed in runs:
        reachable: set[str] = allowed or brand_locations(brand)
        brand.world.storage_scope.entered.clear()
        response = call_brand(brand, operation, headers)
        entered = list(brand.world.storage_scope.entered)
        reachable |= allowed or brand_locations(brand)
        foreign = [
            (item.kind.value, item.business_id)
            for item in entered
            if item.kind is not StorageScopeKind.BUSINESS
            or str(item.business_id) not in reachable
        ]
        if response.status_code in (401, 403, 404) or foreign:
            failures.append(
                f"{operation.key}: {response.status_code} {response.text[:120]} "
                f"scopes outside the brand: {foreign}"
            )

    return failures
