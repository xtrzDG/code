"""Opening a resolved handoff again: its status, its conversation, audit, events."""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.handoffs import HandoffResult
from app.schemas.dto.operations.handoffs import (
    HandoffListItem,
    ReopenHandoffCommand,
    ResolveHandoffCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.handoff_fixture import HandoffFixture

STAFF_ID: UserId = UserId()


def resolve(fixture: HandoffFixture, handoff: HandoffResult) -> HandoffListItem:
    return fixture.world.resolve_handoff().run(
        ResolveHandoffCommand(
            business_id=fixture.business.id, handoff_id=handoff.id, actor_id=STAFF_ID
        )
    )


def reopen(fixture: HandoffFixture, handoff_id: HandoffId) -> HandoffListItem:
    return fixture.world.reopen_handoff().run(
        ReopenHandoffCommand(
            business_id=fixture.business.id, actor_id=STAFF_ID, handoff_id=handoff_id
        )
    )


def test_reopen_brings_back_the_status_and_silences_the_assistant() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    handoff = fixture.hand_off()
    resolve(fixture, handoff)
    assert fixture.conversation_status() is ConversationStatus.OPEN
    stored = fixture.world.handoff_repo.get(fixture.business.id, handoff.id)
    assert stored is not None and stored.resolved_by == STAFF_ID
    assert stored.status_before_resolve is HandoffStatus.PENDING

    reopened = reopen(fixture, handoff.id)

    assert reopened.status is HandoffStatus.PENDING
    assert reopened.resolved_at is None
    assert fixture.conversation_status() is ConversationStatus.HANDOFF
    entries = fixture.world.audit_repo.list_by_business(fixture.business.id)
    assert [(entry.action, str(entry.entity)) for entry in entries] == [
        (AuditAction.UPDATE, "handoff"),
        (AuditAction.UPDATE, "handoff"),
    ]
    assert fixture.world.live_events.kinds()[-2:] == [
        LiveEventKind.HANDOFF_RESOLVED,
        LiveEventKind.HANDOFF_REOPENED,
    ]
    again = fixture.world.handoff_repo.get(fixture.business.id, handoff.id)
    assert again is not None
    assert again.status_before_resolve is None and again.resolved_by is None


def test_reopening_an_open_handoff_is_harmless() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    handoff = fixture.hand_off()
    events_before = len(fixture.world.live_events.events)

    assert reopen(fixture, handoff.id).status is HandoffStatus.PENDING
    assert len(fixture.world.live_events.events) == events_before
    assert fixture.world.audit_repo.list_by_business(fixture.business.id) == []
    with pytest.raises(NotFoundError):
        reopen(fixture, HandoffId())


def test_a_handoff_resolved_before_this_release_reopens_as_notified() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    handoff = fixture.hand_off()
    resolve(fixture, handoff)
    stored = fixture.world.handoff_repo.get(fixture.business.id, handoff.id)
    assert stored is not None
    fixture.world.handoff_repo.save(
        stored.model_copy(update={"status_before_resolve": None})
    )

    assert reopen(fixture, handoff.id).status is HandoffStatus.NOTIFIED


def test_a_closed_conversation_stays_closed_and_others_keep_their_handoff() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    first, second = fixture.hand_off(), fixture.hand_off()
    resolve(fixture, first)
    # The second handoff still holds the conversation for a person.
    assert fixture.conversation_status() is ConversationStatus.HANDOFF
    reopen(fixture, first.id)
    assert fixture.conversation_status() is ConversationStatus.HANDOFF

    resolve(fixture, first)
    resolve(fixture, second)
    conversation = fixture.world.conversation_repo.get(
        fixture.business.id, fixture.conversation.id
    )
    assert conversation is not None
    fixture.world.conversation_repo.save(
        conversation.model_copy(update={"status": ConversationStatus.CLOSED})
    )
    reopen(fixture, second.id)
    assert fixture.conversation_status() is ConversationStatus.CLOSED


def test_resolving_without_a_staff_member_is_not_audited() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    handoff = fixture.hand_off()
    fixture.world.resolve_handoff().run(
        ResolveHandoffCommand(business_id=fixture.business.id, handoff_id=handoff.id)
    )

    assert fixture.world.audit_repo.list_by_business(fixture.business.id) == []
