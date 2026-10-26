"""
A deletion that fails half-way is retried by the queue and continues from
the stage its ledger entry recorded: the providers are not switched off a
second time, the files not erased again, and the business still ends with
nothing left but what the law keeps.
"""

from collections.abc import Callable

import pytest

from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.utilities.business_closures.retained_tables import RETAINED_TABLES
from tests.business_closures.closure_world import (
    DAY_SECONDS,
    ClosureWorld,
    open_closure_world,
)

FAILING_TABLE: str = "contacts"


class EraserOutage(RuntimeError):
    """The storage gives way once while the business's contacts go."""


def fail_once(world: ClosureWorld, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The first removal of the contacts table fails; later ones work."""

    failures: list[int] = []
    registry = world.workshop.container.clients.in_memory_collections()
    for name, table in registry.tables():
        if str(name) != FAILING_TABLE:
            continue

        original: Callable[[BusinessId], DocumentCount] = (
            table.remove_business_documents
        )

        def failing(
            business_id: BusinessId,
            original: Callable[[BusinessId], DocumentCount] = original,
        ) -> DocumentCount:
            if not failures:
                failures.append(1)
                raise EraserOutage("the contacts table is unavailable")
            return original(business_id)

        monkeypatch.setattr(table, "remove_business_documents", failing)

    return failures


def ledger_entry(world: ClosureWorld) -> BusinessDeletionDocument:
    container = world.workshop.container
    with container.utilities.storage_scope().platform_wide():
        entry = container.repositories.business_deletion_repo().find_by_business(
            BusinessId(world.business_b)
        )
    assert entry is not None
    return entry


def test_a_failed_deletion_continues_where_it_stopped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with open_closure_world() as world:
        failures = fail_once(world, monkeypatch)
        before_a = world.rows_of(world.business_a)
        world.close_b()
        world.workshop.clock.advance(31 * DAY_SECONDS)
        world.tick("queue_business_deletions")

        world.workshop.run_queued_jobs()

        assert failures == [1]
        stopped = ledger_entry(world)
        assert stopped.completed_at is None
        assert stopped.deprovisioned_at is not None
        assert stopped.files_erased_at is not None
        assert stopped.rows_counted_at is not None

        world.workshop.clock.advance(60 * 60)
        world.workshop.run_queued_jobs()

        finished = ledger_entry(world)
        assert finished.completed_at is not None
        assert finished.certificate_digest is not None
        assert finished.deprovisioned_at == stopped.deprovisioned_at
        assert finished.deprovisioned == stopped.deprovisioned
        assert finished.files_erased_at == stopped.files_erased_at
        assert finished.erased_rows == stopped.erased_rows
        left = world.rows_of(world.business_b)
        assert set(left) - set(RETAINED_TABLES) <= {"queued_jobs"}
        assert FAILING_TABLE not in left
        assert world.rows_of(world.business_a) == before_a
