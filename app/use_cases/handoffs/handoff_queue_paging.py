"""
The order of the handoffs list as keyset phases: open handoffs of each
urgency (the most urgent first, the oldest first within one), then the
resolved ones (the most recently resolved first).

The cursor keeps the single sort key the list always had: open handoffs
rank above `OPEN_BAND` by urgency band minus their creation time, resolved
ones by their resolution time. A cursor names its phase and the position
inside it; a page reads phase after phase until it has the page size plus
one handoff.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.contracts.repositories.booking_repositories import HandoffRepoContract
from app.schemas.constants.handoffs import HandoffStatus, HandoffUrgency
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.listing_filters import HandoffListFilter
from app.schemas.dto.paging import KeysetPosition, KeysetSlice, PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.booleans import IsHandoffOpen
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.utilities.paging.cursor_paging import decode_page_cursor
from app.utilities.paging.keyset_paging import single_value_position

# Sort-key bands (keys are compared descending): every open handoff above
# every resolved one, and within open ones a more urgent one above an older
# one. Timestamps in microseconds stay far below URGENCY_BAND.
OPEN_BAND: int = 10**19
URGENCY_BAND: int = 10**17
URGENCY_RANK: dict[HandoffUrgency, int] = {
    HandoffUrgency.LOW: 0,
    HandoffUrgency.NORMAL: 1,
    HandoffUrgency.HIGH: 2,
    HandoffUrgency.CRITICAL: 3,
}
URGENCIES_FIRST_TO_LAST: tuple[HandoffUrgency, ...] = tuple(
    sorted(URGENCY_RANK, key=lambda urgency: URGENCY_RANK[urgency], reverse=True)
)

type PhaseReader = Callable[[KeysetSlice], list[HandoffDocument]]


@dataclass(frozen=True)
class QueuePhase:
    """One phase of the list: open handoffs of an urgency, or resolved ones."""

    urgency: HandoffUrgency | None


RESOLVED_PHASE: QueuePhase = QueuePhase(urgency=None)


def is_open(handoff: HandoffDocument) -> bool:
    """A handoff waits for a person until staff resolve it."""

    return handoff.status is not HandoffStatus.RESOLVED


def handoff_sort_key(handoff: HandoffDocument) -> int:
    """Open first (most urgent, then oldest), then latest resolved first."""

    if is_open(handoff):
        return (
            OPEN_BAND
            + URGENCY_RANK[handoff.urgency] * URGENCY_BAND
            - int(handoff.created_at)
        )

    return int(handoff.resolved_at or handoff.created_at)


def listed_phases(
    status: HandoffStatus | None, open_only: IsHandoffOpen | None
) -> list[QueuePhase]:
    """The phases the filters keep, in list order."""

    wants_open: bool = open_only is not False and status is not HandoffStatus.RESOLVED
    wants_resolved: bool = open_only is not True and status in (
        None,
        HandoffStatus.RESOLVED,
    )
    phases: list[QueuePhase] = (
        [QueuePhase(urgency=urgency) for urgency in URGENCIES_FIRST_TO_LAST]
        if wants_open
        else []
    )
    return [*phases, RESOLVED_PHASE] if wants_resolved else phases


def read_queue_page(
    handoff_repo: HandoffRepoContract,
    business_id: BusinessId,
    page: PageRequest,
    listing: HandoffListFilter,
    open_only: IsHandoffOpen | None,
) -> list[HandoffDocument]:
    """
    The page size plus one handoffs after the cursor, phase by phase.

    Raises:
        ValidationFailedError: the cursor is broken.
    """

    phases: list[QueuePhase] = listed_phases(listing.status, open_only)
    after: KeysetPosition | None = None
    if page.cursor is not None:
        start, after = cursor_position(*decode_page_cursor(page.cursor))
        phases = phases[phases.index(start) :] if start in phases else []

    needed: int = int(page.size) + 1
    found: list[HandoffDocument] = []
    for phase in phases:
        found.extend(
            read_phase(handoff_repo, business_id, phase, listing)(
                KeysetSlice(after=after, limit=KeysetReadLimit(needed - len(found)))
            )
        )
        after = None
        if len(found) >= needed:
            break

    return found


def read_phase(
    handoff_repo: HandoffRepoContract,
    business_id: BusinessId,
    phase: QueuePhase,
    listing: HandoffListFilter,
) -> PhaseReader:
    urgency: HandoffUrgency | None = phase.urgency
    if urgency is None:
        return lambda window: handoff_repo.page_resolved(
            business_id, window, listing.include_sandbox
        )

    return lambda window: handoff_repo.page_open(business_id, urgency, window, listing)


def cursor_position(sort_key: int, item_id: str) -> tuple[QueuePhase, KeysetPosition]:
    """The phase a cursor's sort key belongs to, and the position inside it."""

    if sort_key < OPEN_BAND:
        return RESOLVED_PHASE, single_value_position(sort_key, item_id)

    above_open: int = sort_key - OPEN_BAND
    rank: int = min(
        max(-(-above_open // URGENCY_BAND), URGENCY_RANK[HandoffUrgency.LOW]),
        URGENCY_RANK[HandoffUrgency.CRITICAL],
    )
    urgency: HandoffUrgency = next(
        found for found, value in URGENCY_RANK.items() if value == rank
    )
    return QueuePhase(urgency=urgency), single_value_position(
        rank * URGENCY_BAND - above_open, item_id
    )
