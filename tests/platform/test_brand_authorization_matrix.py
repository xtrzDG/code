"""
Authorization matrix of the brands (R17-BRANDS), generated from the API
description like the business matrix:

- every operation under /v1/brands/{brand_id}: strangers (another
  business's owner and staff, and B's own staff, none of them on the
  brand's team) get 404, a caller without a valid token 401, a regional
  manager 403 on the owners' operations, each without touching the store
  or any storage scope; members are let through and touch only the
  storage scopes of the brand's locations they reach;
- through the brand, every business operation of a location keeps its
  rules: a regional manager of C gets 404 on all of B's operations;
  assigned to B, they are staff there (403 on the owner's operations);
  a brand owner who is not on B's own team owns it;
- taking someone off the brand, or a location out of it, ends that
  access at the next request;
- a location's two-factor rule for its team holds for the brand's owners'
  operations and for joining a brand (tests/platform/brand_two_factor_checks.py).

The same runs on Postgres with row-level security in
tests/storage/test_brand_authorization_matrix_postgres.py.
"""

from collections.abc import Iterator

import pytest

from tests.platform.authorization_checks import check_refusals, expect_error
from tests.platform.brand_access_checks import (
    check_brand_roles_on_business_operations,
    check_revocation_at_next_request,
)
from tests.platform.brand_matrix_checks import (
    BRAND_OWNER_ONLY,
    brand_operations,
    check_brand_refusals,
    check_members_reach_only_their_locations,
)
from tests.platform.brand_matrix_world import BrandWorld, open_brand_world
from tests.platform.brand_two_factor_checks import (
    check_brand_owner_actions_need_two_factors,
    check_joining_a_brand_needs_two_factors,
)

MINIMUM_BRAND_OPERATIONS: int = 14


@pytest.fixture(scope="module")
def brand() -> Iterator[BrandWorld]:
    with open_brand_world() as opened:
        yield opened


def test_the_matrix_covers_every_brand_operation(brand: BrandWorld) -> None:
    keys = {item.key for item in brand_operations(brand.world.workshop.application)}

    assert len(keys) >= MINIMUM_BRAND_OPERATIONS
    assert sorted(BRAND_OWNER_ONLY - keys) == []


def test_strangers_to_the_brand_get_not_found(brand: BrandWorld) -> None:
    expected = expect_error(404, "not_found")
    world = brand.world

    assert check_brand_refusals(brand, world.owner_a, expected) == []
    assert check_brand_refusals(brand, world.staff_a, expected) == []
    assert check_brand_refusals(brand, world.staff_b, expected) == []


def test_requests_without_a_valid_token_get_authentication_required(
    brand: BrandWorld,
) -> None:
    expected = expect_error(401, "authentication_required")

    assert check_brand_refusals(brand, {}, expected) == []
    assert check_brand_refusals(brand, {"Authorization": "Bearer x"}, expected) == []


def test_a_regional_manager_gets_access_denied_on_the_owners_operations(
    brand: BrandWorld,
) -> None:
    expected = expect_error(403, "access_denied")

    assert check_brand_refusals(brand, brand.manager, expected, BRAND_OWNER_ONLY) == []


def test_a_manager_of_another_location_never_sees_this_one(brand: BrandWorld) -> None:
    # The manager runs C only: B's every operation is as if B did not exist.
    expected = expect_error(404, "not_found")

    assert check_refusals(brand.world, brand.manager, expected) == []


def test_the_brand_roles_keep_the_business_rules() -> None:
    with open_brand_world() as changed:
        assert check_brand_roles_on_business_operations(changed) == []


def test_members_touch_only_the_brand_locations_they_reach() -> None:
    with open_brand_world() as changed:
        assert check_members_reach_only_their_locations(changed) == []


def test_removal_from_the_brand_ends_access_at_the_next_request() -> None:
    with open_brand_world() as changed:
        assert check_revocation_at_next_request(changed) == []


def test_joining_a_brand_follows_the_business_two_factor_rule() -> None:
    with open_brand_world() as changed:
        assert check_joining_a_brand_needs_two_factors(changed) == []


def test_brand_owner_actions_follow_each_location_two_factor_rule() -> None:
    with open_brand_world() as changed:
        assert check_brand_owner_actions_need_two_factors(changed) == []
