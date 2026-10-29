"""
A conversation's team fields belong to their own writes: a plain save from
a turn that read the conversation earlier never undoes an assignment or an
open request, and `awaits_team` always follows the conversation.
"""

from app.schemas.constants.conversations import ConversationStatus
from app.schemas.dto.inbox.assignment import ConversationAssignmentChange
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from tests.inbox.inbox_builders import hand_off, reload, talk
from tests.inbox.inbox_store import InboxStore


def assign_to_staff(store: InboxStore, revision: int = 0) -> None:
    conversation = store.conversation_repo.list_by_business(store.business.id)[0]
    store.conversation_repo.assign(
        store.business.id,
        conversation.id,
        ConversationAssignmentChange(
            assignee_user_id=store.staff.id,
            assigned_by=store.owner.id,
            expected_revision=AssignmentRevision(revision),
            at=store.now,
        ),
    )


def test_a_save_from_an_earlier_read_keeps_the_assignment() -> None:
    store = InboxStore()
    conversation = talk(store, "Nino", minutes_ago=5)
    read_by_the_turn = reload(store, conversation)
    assign_to_staff(store)

    read_by_the_turn.last_message_at = store.later(1)
    store.conversation_repo.save(read_by_the_turn)

    stored = reload(store, conversation)
    assert stored.assignee_user_id == store.staff.id
    assert stored.assigned_by == store.owner.id
    assert stored.assignment_revision == AssignmentRevision(1)
    assert stored.last_message_at == store.now


def test_a_save_keeps_an_open_request_and_derives_waiting_for_the_team() -> None:
    store = InboxStore()
    conversation = talk(store, "Nino", minutes_ago=5)
    stale = reload(store, conversation)
    store.conversation_repo.set_open_request(
        store.business.id, conversation.id, True, store.now
    )

    store.conversation_repo.save(stale)

    stored = reload(store, conversation)
    assert stored.has_open_request is True
    assert stored.awaits_team is True


def test_waiting_for_the_team_follows_the_handoff() -> None:
    store = InboxStore()
    conversation = talk(store, "Nino", minutes_ago=5)
    assert reload(store, conversation).awaits_team is False

    hand_off(store, conversation)
    assert reload(store, conversation).awaits_team is True

    resolved = reload(store, conversation)
    resolved.status = ConversationStatus.OPEN
    store.conversation_repo.save(resolved)
    assert reload(store, conversation).awaits_team is False


def test_a_stale_revision_writes_nothing() -> None:
    store = InboxStore()
    talk(store, "Nino", minutes_ago=5)
    assign_to_staff(store)
    conversation = store.conversation_repo.list_by_business(store.business.id)[0]

    refused = store.conversation_repo.assign(
        store.business.id,
        conversation.id,
        ConversationAssignmentChange(
            assignee_user_id=store.colleague.id,
            assigned_by=store.owner.id,
            expected_revision=AssignmentRevision(0),
            at=store.now,
        ),
    )

    assert refused is None
    assert reload(store, conversation).assignee_user_id == store.staff.id


def test_unassigning_clears_who_and_when_but_counts_the_revision() -> None:
    store = InboxStore()
    conversation = talk(store, "Nino", minutes_ago=5)
    assign_to_staff(store)

    released = store.conversation_repo.assign(
        store.business.id,
        conversation.id,
        ConversationAssignmentChange(
            assignee_user_id=None,
            assigned_by=store.staff.id,
            expected_revision=AssignmentRevision(1),
            at=store.later(3),
        ),
    )

    assert released is not None
    assert released.assignee_user_id is None
    assert released.assigned_by is None
    assert released.assigned_at is None
    assert released.assignment_revision == AssignmentRevision(2)


def test_bulk_loads_write_the_team_fields_as_given() -> None:
    store = InboxStore()
    conversation = talk(store, "Nino", minutes_ago=5)
    loaded = reload(store, conversation).model_copy(
        update={
            "assignee_user_id": store.colleague.id,
            "has_open_request": True,
        }
    )

    store.conversation_repo.save_many([loaded])

    stored = reload(store, conversation)
    assert stored.assignee_user_id == store.colleague.id
    assert stored.awaits_team is True


def test_the_open_request_flag_of_a_missing_conversation_is_none() -> None:
    store = InboxStore()
    conversation = talk(store, "Nino", minutes_ago=5)
    other = InboxStore()

    assert (
        other.conversation_repo.set_open_request(
            other.business.id, conversation.id, True, other.now
        )
        is None
    )
