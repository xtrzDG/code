"""
The authorization matrix (tests/platform/test_authorization_matrix.py) on
Postgres, where row-level security is the second line of defence: every
business operation refuses strangers (404), staff on owner-only operations
(403) and callers without a token (401) without changing a row, and lets
members through inside their business's scope.
"""

from app.schemas.typings.platform.strings import DatabaseUrl
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.platform.authorization_checks import (
    check_members_are_let_through,
    check_owner_reads_every_record,
    check_refusals,
    expect_error,
)
from tests.platform.authorization_tables import OWNER_ONLY_OPERATIONS
from tests.platform.authorization_world import open_authorization_world


def test_every_business_operation_refuses_outsiders_on_postgres(
    database_url: DatabaseUrl,
) -> None:
    environment = {**E2E_ENVIRONMENT, "DATABASE_URL": str(database_url)}
    with open_authorization_world(environment) as world:
        failures = (
            check_owner_reads_every_record(world)
            + check_refusals(world, world.owner_a, expect_error(404, "not_found"))
            + check_refusals(world, world.staff_a, expect_error(404, "not_found"))
            + check_refusals(world, {}, expect_error(401, "authentication_required"))
            + check_refusals(
                world,
                world.staff_b,
                expect_error(403, "access_denied"),
                only=OWNER_ONLY_OPERATIONS,
            )
        )

    assert failures == []


def test_members_are_let_through_in_their_business_scope_on_postgres(
    database_url: DatabaseUrl,
) -> None:
    environment = {**E2E_ENVIRONMENT, "DATABASE_URL": str(database_url)}
    with open_authorization_world(environment) as world:
        failures = check_members_are_let_through(world)

    assert failures == []
