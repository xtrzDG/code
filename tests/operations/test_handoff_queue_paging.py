"""The handoff list read phase by phase: every page in the list order."""

import random

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.operations.handoffs import HandoffPage, ListHandoffsQuery
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.handoffs.handoff_queue_paging import (
    OPEN_BAND,
    URGENCY_BAND,
    cursor_position,
    handoff_sort_key,
)
from tests.operations.handoff_fixture import HandoffFixture

START: int = 1_790_000_000_000_000


def seed_queue(fixture: HandoffFixture, count: int) -> list[HandoffDocument]:
    """Handoffs of every urgency and status at distinct times, some sandbox."""

    chooser = random.Random(42)
    handoffs: list[HandoffDocument] = []
    for index in range(count):
        status: HandoffStatus = chooser.choice(list(HandoffStatus))
        created_at = Microseconds(START + index * 60_000_000)
        handoff = HandoffDocument(
            business_id=fixture.business.id,
            conversation_id=fixture.conversation.id,
            contact_id=fixture.contact.id,
            reason=chooser.choice(list(HandoffReason)),
            summary=HandoffSummary(f"Handoff {index}"),
            urgency=chooser.choice(list(HandoffUrgency)),
            status=status,
            resolved_at=(
                Microseconds(START + chooser.randrange(10**9, 10**11))
                if status is HandoffStatus.RESOLVED
                else None
            ),
            is_sandbox=index % 7 == 0,
            created_at=created_at,
            updated_at=created_at,
        )
        fixture.world.handoff_repo.save(handoff)
        handoffs.append(handoff)

    return handoffs


def walk(fixture: HandoffFixture, size: int, **filters: object) -> list[HandoffPage]:
    pages: list[HandoffPage] = []
    cursor: PageCursor | None = None
    while True:
        page: HandoffPage = fixture.world.list_handoffs().run(
            ListHandoffsQuery.model_validate(
                {
                    "business_id": fixture.business.id,
                    "actor_id": UserId(),
                    "page": PageRequest(size=PageSize(size), cursor=cursor),
                    **filters,
                }
            )
        )
        pages.append(page)
        if page.next_cursor is None:
            return pages
        cursor = page.next_cursor


@pytest.mark.parametrize("size", [1, 2, 5])
def test_pages_follow_the_queue_order_through_every_phase(size: int) -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    handoffs = seed_queue(fixture, 40)
    real = [handoff for handoff in handoffs if not handoff.is_sandbox]
    expected = sorted(real, key=handoff_sort_key, reverse=True)

    pages = walk(fixture, size)

    assert [item.id for page in pages for item in page.items] == [
        handoff.id for handoff in expected
    ]
    assert all(len(page.items) == size for page in pages[:-1])
    resolved = sum(1 for h in real if h.status is HandoffStatus.RESOLVED)
    assert (int(pages[0].open_count), int(pages[0].resolved_count)) == (
        len(real) - resolved,
        resolved,
    )


@pytest.mark.parametrize(
    ("filters", "kept_statuses"),
    [
        ({"is_open": True}, set(HandoffStatus) - {HandoffStatus.RESOLVED}),
        ({"is_open": False}, {HandoffStatus.RESOLVED}),
        ({"status": HandoffStatus.NOTIFIED}, {HandoffStatus.NOTIFIED}),
        ({"status": HandoffStatus.RESOLVED}, {HandoffStatus.RESOLVED}),
        ({"status": HandoffStatus.RESOLVED, "is_open": True}, set[HandoffStatus]()),
    ],
)
def test_filters_keep_the_order_of_their_phases(
    filters: dict[str, object], kept_statuses: set[HandoffStatus]
) -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    handoffs = seed_queue(fixture, 30)
    expected = sorted(
        (h for h in handoffs if not h.is_sandbox and h.status in kept_statuses),
        key=handoff_sort_key,
        reverse=True,
    )

    pages = walk(fixture, 3, include_sandbox=False, **filters)

    assert [item.id for page in pages for item in page.items] == [
        handoff.id for handoff in expected
    ]


def test_a_cursor_names_its_phase_and_position() -> None:
    phase, position = cursor_position(OPEN_BAND + 2 * URGENCY_BAND - 1_000, "handoff_x")
    resolved_phase, resolved_position = cursor_position(5_000, "handoff_y")
    clamped, _ = cursor_position(OPEN_BAND + 9 * URGENCY_BAND, "handoff_z")

    assert phase.urgency is HandoffUrgency.HIGH
    assert [int(value) for value in position.sort_values] == [1_000]
    assert resolved_phase.urgency is None
    assert [int(value) for value in resolved_position.sort_values] == [5_000]
    assert clamped.urgency is HandoffUrgency.CRITICAL


def test_a_broken_cursor_is_refused() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    with pytest.raises(ValidationFailedError):
        fixture.world.list_handoffs().run(
            ListHandoffsQuery(
                business_id=fixture.business.id,
                actor_id=UserId(),
                page=PageRequest(cursor=PageCursor("bm90LWEtY3Vyc29y")),
            )
        )
