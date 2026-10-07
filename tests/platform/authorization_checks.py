"""
The checks of the authorization matrix, shared by the in-memory run
(tests/platform/test_authorization_matrix.py) and the Postgres run with
row-level security (tests/storage/test_authorization_matrix_postgres.py).
Each check returns its failures, one line per operation.
"""

from collections.abc import Callable
from typing import cast

from httpx2 import Response

from app.schemas.constants.storage import StorageScopeKind
from tests.platform.authorization_requests import (
    MatrixOperation,
    business_operations,
    call_operation,
)
from tests.platform.authorization_tables import (
    OWNER_ONLY_OPERATIONS,
    PLATFORM_WIDE_LOOKUPS,
    READS_WITHOUT_CONTENT,
    REFUSAL_EXCEPTIONS,
)
from tests.platform.authorization_world import AuthorizationWorld, Headers
from tests.platform.storage_snapshot import describe_changes, take_storage_snapshot

type Expectation = Callable[[Response], str | None]


def operations_of(world: AuthorizationWorld) -> list[MatrixOperation]:
    return business_operations(world.workshop.application)


def expect_error(status_code: int, error_code: str) -> Expectation:
    """The status with an ErrorBody of that code, else what went wrong."""

    def check(response: Response) -> str | None:
        body: object = response.json() if response.content else None
        actual_code: object = (
            cast(dict[str, object], body).get("error")
            if isinstance(body, dict)
            else None
        )
        if response.status_code == status_code and actual_code == error_code:
            return None

        return (
            f"expected {status_code} {error_code}, "
            f"got {response.status_code} {response.text[:160]}"
        )

    return check


def check_owner_reads_every_record(world: AuthorizationWorld) -> list[str]:
    """B's owner reads each record the matrix uses: a stranger's 404 is isolation."""

    failures: list[str] = []
    for operation in operations_of(world):
        if operation.method != "get" or operation.key in READS_WITHOUT_CONTENT:
            continue

        response = call_operation(
            world.workshop.client, operation, world.path_values, world.owner_b
        )
        if response.status_code != 200:
            failures.append(
                f"{operation.key}: {response.status_code} {response.text[:160]}"
            )

    return failures


def check_refusals(
    world: AuthorizationWorld,
    headers: Headers,
    expectation: Expectation,
    only: frozenset[str] | None = None,
) -> list[str]:
    """
    Every operation (or those in `only`) refused as expected, in no scope
    but business B's, and the store unchanged afterwards (no audit entry, no
    view, no write).
    """

    container, storage_scope = world.workshop.container, world.storage_scope
    before = take_storage_snapshot(container, storage_scope)
    failures: list[str] = []
    for operation in operations_of(world):
        if (only is not None and operation.key not in only) or (
            operation.key in REFUSAL_EXCEPTIONS
        ):
            continue

        storage_scope.entered.clear()
        response = call_operation(
            world.workshop.client, operation, world.path_values, headers
        )
        problem: str | None = expectation(response) or foreign_scope(world, operation)
        if problem is not None:
            failures.append(f"{operation.key}: {problem}")

    changes = describe_changes(before, take_storage_snapshot(container, storage_scope))
    return failures + [
        f"refused requests changed the store: {change}" for change in changes
    ]


def check_members_are_let_through(world: AuthorizationWorld) -> list[str]:
    """
    Staff may use every operation that is not owner-only, the owner the
    owner-only ones; each such request runs in business B's scope (reads
    first, then changes; the owner's run removes staff, so it comes last).
    """

    failures: list[str] = []
    by_reads_first = sorted(operations_of(world), key=lambda item: item.method != "get")
    staff_run = [
        item for item in by_reads_first if item.key not in OWNER_ONLY_OPERATIONS
    ]
    owner_run = [item for item in by_reads_first if item.key in OWNER_ONLY_OPERATIONS]
    for headers, operations in ((world.staff_b, staff_run), (world.owner_b, owner_run)):
        for operation in operations:
            world.storage_scope.entered.clear()
            response = call_operation(
                world.workshop.client, operation, world.path_values, headers
            )
            problem: str | None = (
                f"refused with {response.status_code}"
                if response.status_code in (401, 403)
                else foreign_scope(world, operation, must_enter=True)
            )
            if problem is not None:
                failures.append(f"{operation.key}: {problem}")

    return failures


def foreign_scope(
    world: AuthorizationWorld,
    operation: MatrixOperation,
    must_enter: bool = False,
) -> str | None:
    """Whether the request entered a scope other than business B's."""

    entered = world.storage_scope.entered
    others = [
        scope
        for scope in entered
        if not (
            scope.kind is StorageScopeKind.BUSINESS
            and str(scope.business_id) == world.business_b
        )
        and not (
            scope.kind is StorageScopeKind.PLATFORM
            and operation.key in PLATFORM_WIDE_LOOKUPS
        )
    ]
    if others:
        return f"ran in {[(scope.kind.value, scope.business_id) for scope in others]}"

    if must_enter and not entered:
        return "ran in no business scope"

    return None
