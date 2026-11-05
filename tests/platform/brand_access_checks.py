"""
What the brand roles may do with a location's own operations, and how
removal ends it: the business matrix's checks run with the brand's people
(tests/platform/test_brand_authorization_matrix.py and its Postgres run).
"""

from tests.platform.authorization_checks import (
    Expectation,
    check_refusals,
    expect_error,
    foreign_scope,
    operations_of,
)
from tests.platform.authorization_requests import call_operation
from tests.platform.authorization_tables import OWNER_ONLY_OPERATIONS
from tests.platform.authorization_world import Headers
from tests.platform.brand_matrix_world import BrandWorld

B: str = "/v1/businesses/{business_id}"
LEAVE_BRAND: str = f"DELETE {B}/brand"

# The rule a regional manager keeps as staff: a note is deleted by its
# author or an owner (B's own staff member wrote it). A brand owner acts as
# an owner everywhere, support access decisions included.
KEPT_REFUSALS: dict[str, Expectation] = {
    f"DELETE {B}/conversations/{{conversation_id}}/notes/{{note_id}}": expect_error(
        403, "access_denied"
    ),
}


def assign_manager(brand: BrandWorld, business_ids: list[str]) -> None:
    changed = brand.world.workshop.client.patch(
        f"/v1/brands/{brand.brand_id}/members/{brand.manager_id}",
        json={"role": "regional_manager", "business_ids": business_ids},
        headers=brand.world.owner_b,
    )
    assert changed.status_code == 200, changed.text


def check_brand_roles_on_business_operations(brand: BrandWorld) -> list[str]:
    """
    A manager assigned to B is staff there (403 on the owner's operations,
    let through on the rest); the co-owner, on the brand's team but not on
    B's own, may use B's owner-only operations; each request stays in B's
    scope. Leaving the brand comes last, as it ends the co-owner's access.
    """

    world = brand.world
    assign_manager(brand, [world.business_b, brand.location_c])
    failures: list[str] = check_refusals(
        world, brand.manager, expect_error(403, "access_denied"), OWNER_ONLY_OPERATIONS
    )
    by_reads_first = sorted(
        operations_of(world),
        key=lambda item: (item.method != "get", item.key == LEAVE_BRAND),
    )
    runs: list[tuple[Headers, bool]] = [(brand.manager, False), (brand.co_owner, True)]
    for headers, is_owner_run in runs:
        for operation in by_reads_first:
            if (operation.key in OWNER_ONLY_OPERATIONS) is not is_owner_run:
                continue

            world.storage_scope.entered.clear()
            response = call_operation(
                world.workshop.client, operation, world.path_values, headers
            )
            kept: Expectation | None = KEPT_REFUSALS.get(operation.key)
            problem: str | None = (
                kept(response)
                if kept is not None
                else f"refused with {response.status_code} {response.text[:120]}"
                if response.status_code in (401, 403)
                or (operation.key == LEAVE_BRAND and response.status_code != 204)
                else foreign_scope(world, operation, must_enter=True)
            )
            if problem is not None:
                failures.append(f"{operation.key}: {problem}")

    return failures


def status_of(brand: BrandWorld, path: str, headers: Headers) -> int:
    return brand.world.workshop.client.get(path, headers=headers).status_code


def check_revocation_at_next_request(brand: BrandWorld) -> list[str]:
    """Every way out of a brand closes its locations at the next request."""

    world, client = brand.world, brand.world.workshop.client
    base = f"/v1/brands/{brand.brand_id}"
    location_b = f"/v1/businesses/{world.business_b}"
    location_c = f"/v1/businesses/{brand.location_c}"
    expected: list[tuple[str, int, int]] = []

    def observe(label: str, path: str, headers: Headers, status: int) -> None:
        expected.append((label, status, status_of(brand, path, headers)))

    observe("manager sees C", location_c, brand.manager, 200)
    observe("manager never sees B", location_b, brand.manager, 404)
    client.delete(f"{base}/members/{brand.manager_id}", headers=world.owner_b)
    observe("removed manager loses C", location_c, brand.manager, 404)
    observe("removed manager loses the brand", base, brand.manager, 404)
    memberships = client.get("/v1/me", headers=brand.manager).json()["memberships"]
    expected.append(("removed manager lists nothing", 0, len(memberships)))

    observe("co-owner owns B", location_b, brand.co_owner, 200)
    client.delete(f"{base}/locations/{world.business_b}", headers=world.owner_b)
    observe("B out of the brand: co-owner loses it", location_b, brand.co_owner, 404)
    observe("the brand keeps C", location_c, brand.co_owner, 200)
    client.delete(f"{location_c}/brand", headers=world.owner_b)
    observe("C left on its own: co-owner loses it", location_c, brand.co_owner, 404)
    observe("C's own owner keeps it", location_c, world.owner_b, 200)
    return [
        f"{label}: expected {wanted}, got {actual}"
        for label, wanted, actual in expected
        if wanted != actual
    ]
