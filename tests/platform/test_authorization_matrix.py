"""
Authorization matrix of every business operation, generated from the API
description: for each operation under /v1/businesses/{business_id}, filled
with real records of business B,

- the owner of another business gets 404 (as if B did not exist), and the
  store is unchanged (no audit entry, no view, no write);
- B's staff get 403 on owner-only operations, and are let through on the
  rest;
- a caller without a valid token gets 401;
- every request runs only in B's storage scope (no other business, no
  platform-wide escalation outside PLATFORM_WIDE_LOOKUPS).

A new operation is covered without touching this file; the tables in
tests/platform/authorization_tables.py name the explicit exceptions. The
same checks run on Postgres with row-level security in
tests/storage/test_authorization_matrix_postgres.py.
"""

from collections.abc import Iterator

import pytest

from tests.platform.authorization_checks import (
    check_members_are_let_through,
    check_owner_reads_every_record,
    check_refusals,
    expect_error,
    operations_of,
)
from tests.platform.authorization_tables import (
    OWNER_ONLY_OPERATIONS,
    PLATFORM_WIDE_LOOKUPS,
    READS_WITHOUT_CONTENT,
    REFUSAL_EXCEPTIONS,
)
from tests.platform.authorization_world import (
    AuthorizationWorld,
    open_authorization_world,
)

MINIMUM_BUSINESS_OPERATIONS: int = 70


@pytest.fixture(scope="module")
def world() -> Iterator[AuthorizationWorld]:
    with open_authorization_world() as opened:
        yield opened


def test_the_matrix_covers_every_business_operation(world: AuthorizationWorld) -> None:
    keys = {operation.key for operation in operations_of(world)}
    named = (
        set(OWNER_ONLY_OPERATIONS)
        | set(PLATFORM_WIDE_LOOKUPS)
        | set(REFUSAL_EXCEPTIONS)
        | set(READS_WITHOUT_CONTENT)
    )

    assert len(keys) >= MINIMUM_BUSINESS_OPERATIONS
    assert sorted(named - keys) == [], "the tables name operations that are gone"


def test_the_owner_reads_every_record_the_matrix_uses(
    world: AuthorizationWorld,
) -> None:
    assert check_owner_reads_every_record(world) == []


def test_another_business_owner_gets_not_found_without_side_effects(
    world: AuthorizationWorld,
) -> None:
    assert check_refusals(world, world.owner_a, expect_error(404, "not_found")) == []


def test_another_business_staff_get_not_found_without_side_effects(
    world: AuthorizationWorld,
) -> None:
    assert check_refusals(world, world.staff_a, expect_error(404, "not_found")) == []


def test_requests_without_a_valid_token_get_authentication_required(
    world: AuthorizationWorld,
) -> None:
    expected = expect_error(401, "authentication_required")

    assert check_refusals(world, {}, expected) == []
    assert check_refusals(world, {"Authorization": "Bearer forged"}, expected) == []


def test_staff_get_access_denied_on_owner_only_operations(
    world: AuthorizationWorld,
) -> None:
    failures = check_refusals(
        world,
        world.staff_b,
        expect_error(403, "access_denied"),
        only=OWNER_ONLY_OPERATIONS,
    )

    assert failures == []


def test_members_are_let_through_and_stay_in_their_business_scope() -> None:
    # A world of its own: the members' requests change business B.
    with open_authorization_world() as changed_world:
        assert check_members_are_let_through(changed_world) == []
