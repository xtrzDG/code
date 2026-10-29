"""
The brand authorization matrix (tests/platform/test_brand_authorization_matrix.py)
on Postgres, where row-level security is the second line of defence: every
brand operation refuses strangers (404), callers without a token (401) and
regional managers on the owners' operations (403) without changing a row;
members touch only the locations they reach; the brand's roles keep each
location's business rules; leaving the brand ends access at the next
request; and a location's two-factor rule for its team holds for joining a
brand and for every brand owner's operation.
"""

from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.platform.authorization_checks import check_refusals, expect_error
from tests.platform.brand_access_checks import (
    check_brand_roles_on_business_operations,
    check_revocation_at_next_request,
)
from tests.platform.brand_matrix_checks import (
    BRAND_OWNER_ONLY,
    check_brand_refusals,
    check_members_reach_only_their_locations,
)
from tests.platform.brand_matrix_world import open_brand_world
from tests.platform.brand_two_factor_checks import (
    check_brand_owner_actions_need_two_factors,
    check_joining_a_brand_needs_two_factors,
)
from tests.storage.postgres_roles import RoleDatabase


def environment_of(role_urls: RoleDatabase) -> dict[str, str]:
    """The application on its tenant and platform pools (migration 1200)."""

    return {**E2E_ENVIRONMENT, **role_urls.environment()}


def test_brand_operations_refuse_outsiders_on_postgres(
    role_urls: RoleDatabase,
) -> None:
    not_found = expect_error(404, "not_found")
    with open_brand_world(environment_of(role_urls)) as brand:
        world = brand.world
        failures = (
            check_brand_refusals(brand, world.owner_a, not_found)
            + check_brand_refusals(brand, world.staff_a, not_found)
            + check_brand_refusals(brand, world.staff_b, not_found)
            + check_brand_refusals(
                brand, {}, expect_error(401, "authentication_required")
            )
            + check_brand_refusals(
                brand,
                brand.manager,
                expect_error(403, "access_denied"),
                BRAND_OWNER_ONLY,
            )
            + check_refusals(world, brand.manager, not_found)
            + check_members_reach_only_their_locations(brand)
        )

    assert failures == []


def test_brand_roles_keep_the_business_rules_on_postgres(
    role_urls: RoleDatabase,
) -> None:
    with open_brand_world(environment_of(role_urls)) as brand:
        failures = check_brand_roles_on_business_operations(brand)

    assert failures == []


def test_leaving_the_brand_ends_access_at_the_next_request_on_postgres(
    role_urls: RoleDatabase,
) -> None:
    with open_brand_world(environment_of(role_urls)) as brand:
        failures = check_revocation_at_next_request(brand)

    assert failures == []


def test_locations_two_factor_rule_holds_for_the_brand_on_postgres(
    role_urls: RoleDatabase,
) -> None:
    with open_brand_world(environment_of(role_urls)) as brand:
        failures = check_joining_a_brand_needs_two_factors(
            brand
        ) + check_brand_owner_actions_need_two_factors(brand)

    assert failures == []
