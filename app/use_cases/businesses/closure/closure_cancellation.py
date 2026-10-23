"""Cancelling a closure, by an owner or because the unpaid service was paid."""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument
from app.use_cases.businesses.closure.closure_effects import ClosureEffects


def cancel_closure(
    closure_repo: BusinessClosureRepoContract,
    effects: ClosureEffects,
    business: BusinessDocument,
    now: Microseconds,
) -> BusinessClosureDocument | None:
    """
    The closure is marked cancelled, its effects undone and then removed;
    None, and nothing changed, when its deletion is queued already. A
    cancel that dies half-way leaves a cancelled closure, which counts as
    none (the next closure replaces it).
    """

    taken: BusinessClosureDocument | None = take_pending_closure(
        closure_repo, business, now
    )
    if taken is None:
        return None

    effects.restore(taken, now)
    closure_repo.remove(business.id)
    return taken


def take_pending_closure(
    closure_repo: BusinessClosureRepoContract,
    business: BusinessDocument,
    now: Microseconds,
) -> BusinessClosureDocument | None:
    """
    The closure, marked cancelled in one step while its deletion is not
    queued (the sweep marks `deletion_queued_at` in the same kind of step
    and skips a cancelled closure, so a cancel and the sweep never both
    win); None when the deletion is queued.
    """

    def claim(closure: BusinessClosureDocument) -> BusinessClosureDocument | None:
        if closure.deletion_queued_at is not None:
            return None

        closure.cancelled_at = closure.cancelled_at or now
        closure.updated_at = now
        return closure

    return closure_repo.modify(business.id, claim)
