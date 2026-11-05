"""Internal notes: written, read and deleted by the team, always audited."""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.conversation_notes import (
    ConversationNotePage,
    ConversationNotesQuery,
    ConversationNoteView,
    CreateConversationNoteCommand,
    DeleteConversationNoteCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from app.schemas.typings.inbox.prefixed_id import ConversationNoteId
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.prefixed_id import UserId
from tests.inbox.inbox_builders import talk
from tests.inbox.inbox_world import InboxWorld


def write(
    world: InboxWorld,
    conversation: ConversationDocument,
    author: UserId,
    text: str,
) -> ConversationNoteView:
    note = world.create_note().run(
        CreateConversationNoteCommand(
            user_id=author,
            business_id=world.business.id,
            conversation_id=conversation.id,
            text=ConversationNoteText(text),
        )
    )
    world.later(1)
    return note


def read(
    world: InboxWorld,
    conversation: ConversationDocument,
    viewer: UserId,
    size: int = 50,
    cursor: str | None = None,
) -> ConversationNotePage:
    return world.list_notes().run(
        ConversationNotesQuery.model_validate(
            {
                "user_id": viewer,
                "business_id": world.business.id,
                "conversation_id": conversation.id,
                "page": PageRequest.model_validate(
                    {"size": PageSize(size), "cursor": cursor}
                ),
            }
        )
    )


def delete(
    world: InboxWorld,
    conversation: ConversationDocument,
    note_id: ConversationNoteId,
    caller: UserId,
) -> None:
    world.delete_note().run(
        DeleteConversationNoteCommand(
            user_id=caller,
            business_id=world.business.id,
            conversation_id=conversation.id,
            note_id=note_id,
        )
    )


def test_notes_are_read_newest_first_with_their_authors() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3)
    write(world, conversation, world.staff.id, "Called back, no answer.")
    write(world, conversation, world.owner.id, "VIP: give the window table.")

    notes = read(world, conversation, world.staff.id).items

    assert [(str(note.author_name), str(note.text)) for note in notes] == [
        ("Nino", "VIP: give the window table."),
        ("Giorgi", "Called back, no answer."),
    ]
    assert [note.can_delete for note in notes] == [False, True]
    assert [
        note.can_delete for note in read(world, conversation, world.owner.id).items
    ] == [
        True,
        True,
    ]


def test_long_histories_page_back() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3)
    for number in range(5):
        write(world, conversation, world.staff.id, f"Note {number}")

    first = read(world, conversation, world.staff.id, size=2)
    second = read(world, conversation, world.staff.id, size=2, cursor=first.next_cursor)
    rest = read(world, conversation, world.staff.id, size=2, cursor=second.next_cursor)

    assert [str(note.text) for note in [*first.items, *second.items, *rest.items]] == [
        "Note 4",
        "Note 3",
        "Note 2",
        "Note 1",
        "Note 0",
    ]
    assert rest.next_cursor is None


def test_writing_reading_and_deleting_are_audited_and_announced() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3)
    note = write(world, conversation, world.staff.id, "Allergic to nuts.")
    read(world, conversation, world.owner.id)
    delete(world, conversation, note.id, world.staff.id)

    trail = [
        (entry.action, str(entry.entity), str(entry.entity_id), entry.actor_id)
        for entry in world.audit_entries()
    ]
    assert trail == [
        (AuditAction.CREATE, "conversation_note", str(note.id), world.staff.id),
        (AuditAction.VIEW, "conversation_note", str(conversation.id), world.owner.id),
        (AuditAction.DELETE, "conversation_note", str(note.id), world.staff.id),
    ]
    assert [event.event for event in world.live_events.events] == [
        LiveEventKind.CONVERSATION_NOTE,
        LiveEventKind.CONVERSATION_NOTE,
    ]
    assert read(world, conversation, world.owner.id).items == []


def test_staff_delete_only_their_own_notes_and_owners_any() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3)
    owners = write(world, conversation, world.owner.id, "Owner's note")
    colleagues = write(world, conversation, world.colleague.id, "Ana's note")

    with pytest.raises(AccessDeniedError) as refused:
        delete(world, conversation, owners.id, world.staff.id)
    delete(world, conversation, colleagues.id, world.owner.id)

    assert [str(reason.code) for reason in refused.value.reasons] == ["not_note_author"]
    assert [note.id for note in read(world, conversation, world.owner.id).items] == [
        owners.id
    ]


def test_a_note_of_another_conversation_or_business_is_not_found() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3)
    other = talk(world, "Dato", minutes_ago=2)
    note = write(world, conversation, world.owner.id, "Note")

    with pytest.raises(NotFoundError):
        delete(world, other, note.id, world.owner.id)
    with pytest.raises(NotFoundError):
        delete(world, conversation, ConversationNoteId(), world.owner.id)
    with pytest.raises(NotFoundError):
        write(world, talk(InboxWorld(), "Guest", 1), world.owner.id, "Note")
    with pytest.raises(NotFoundError):
        read(world, conversation, world.stranger.id)


def test_test_chat_notes_are_not_announced() -> None:
    world = InboxWorld()
    test_chat = talk(world, "Owner", minutes_ago=1, is_sandbox=True)

    write(world, test_chat, world.owner.id, "Trying the notes.")

    assert world.live_events.events == []
