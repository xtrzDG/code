"""Resolving handoffs and the cabinet's handoff list: filters, audit, order."""

from datetime import datetime

import pytest

from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffStatus, HandoffUrgency
from app.schemas.dto.handoffs import HandoffResult
from app.schemas.dto.operations.handoffs import (
    HandoffPage,
    ListHandoffsQuery,
    ResolveHandoffCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.handoff_fixture import HandoffFixture


def test_resolving_reopens_the_conversation_after_the_last_open_handoff() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    first = fixture.hand_off()
    second = fixture.hand_off()
    resolve = fixture.world.resolve_handoff()

    resolved_first = resolve.run(
        ResolveHandoffCommand(business_id=fixture.business.id, handoff_id=first.id)
    )
    assert resolved_first.status is HandoffStatus.RESOLVED
    assert resolved_first.resolved_at is not None
    assert fixture.conversation_status() is ConversationStatus.HANDOFF

    fixture.world.clock.move_to(datetime.fromisoformat("2026-10-05T12:00:00+03:00"))
    resolved_second = resolve.run(
        ResolveHandoffCommand(business_id=fixture.business.id, handoff_id=second.id)
    )
    assert fixture.conversation_status() is ConversationStatus.OPEN
    assert resolved_second.contact_phone_number == "+972502345678"

    again = resolve.run(
        ResolveHandoffCommand(business_id=fixture.business.id, handoff_id=second.id)
    )
    assert again.resolved_at == resolved_second.resolved_at
    with pytest.raises(NotFoundError):
        resolve.run(
            ResolveHandoffCommand(
                business_id=fixture.business.id, handoff_id=HandoffId()
            )
        )


def test_list_handoffs_filters_and_audits() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    fixture.hand_off()
    fixture.hand_off(is_sandbox=True)
    staff_id = UserId()

    real = fixture.world.list_handoffs().run(
        ListHandoffsQuery(business_id=fixture.business.id, actor_id=staff_id)
    )
    pending = fixture.world.list_handoffs().run(
        ListHandoffsQuery(
            business_id=fixture.business.id,
            actor_id=staff_id,
            status=HandoffStatus.PENDING,
            include_sandbox=True,
        )
    )

    assert [item.status for item in real.items] == [HandoffStatus.NOTIFIED]
    assert real.items[0].contact_name == "Yossi"
    assert real.items[0].urgency is HandoffUrgency.HIGH
    assert len(pending.items) == 1 and pending.items[0].is_sandbox
    assert len(fixture.world.audit_repo.list_by_business(fixture.business.id)) == 2


def test_handoff_pages_put_urgent_and_long_waiting_ones_first() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    urgencies = (
        HandoffUrgency.NORMAL,
        HandoffUrgency.CRITICAL,
        HandoffUrgency.NORMAL,
        HandoffUrgency.HIGH,
    )
    created: list[HandoffResult] = []
    for minute, urgency in enumerate(urgencies):
        fixture.world.clock.move_to(
            datetime.fromisoformat(f"2026-10-05T11:0{minute}:00+03:00")
        )
        created.append(fixture.hand_off(urgency=urgency))
    fixture.world.resolve_handoff().run(
        ResolveHandoffCommand(business_id=fixture.business.id, handoff_id=created[3].id)
    )

    def page(
        is_open: bool | None = None, cursor: PageCursor | None = None
    ) -> HandoffPage:
        return fixture.world.list_handoffs().run(
            ListHandoffsQuery(
                business_id=fixture.business.id,
                actor_id=UserId(),
                is_open=is_open,
                page=PageRequest(size=PageSize(2), cursor=cursor),
            )
        )

    first = page()
    second = page(cursor=first.next_cursor)
    waiting = page(is_open=True)
    done = page(is_open=False)

    ids = [result.id for result in created]
    assert [item.id for item in first.items] == [ids[1], ids[0]]
    assert [item.id for item in second.items] == [ids[2], ids[3]]
    assert second.next_cursor is None
    assert [item.id for item in waiting.items] == [ids[1], ids[0]]
    assert [item.id for item in done.items] == [ids[3]]
    assert (int(done.open_count), int(done.resolved_count)) == (3, 1)
