"""
The brand authorization matrix (tests/platform/test_brand_authorization_matrix.py)
on Postgres, where row-level security is the second line of defence: every
brand operation refuses strangers (404), callers without a token (401) and
regional managers on the owners' operations (403) without changing a row;
members touch only the locations they reach; the brand's roles keep each
location's business rules; and leaving the brand ends access at the next
request.
"""

from app.schemas.typings.platform.strings import DatabaseUrl
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


def environment_of(database_url: DatabaseUrl) -> dict[str, str]:
    return {**E2E_ENVIRONMENT, "DATABASE_URL": str(database_url)}


def test_brand_operations_refuse_outsiders_on_postgres(
    database_url: DatabaseUrl,
) -> None:
    not_found = expect_error(404, "not_found")
    with open_brand_world(environment_of(database_url)) as brand:
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
    database_url: DatabaseUrl,
) -> None:
    with open_brand_world(environment_of(database_url)) as brand:
        failures = check_brand_roles_on_business_operations(brand)

    assert failures == []


def test_leaving_the_brand_ends_access_at_the_next_request_on_postgres(
    database_url: DatabaseUrl,
) -> None:
    with open_brand_world(environment_of(database_url)) as brand:
        failures = check_revocation_at_next_request(brand)

    assert failures == []
