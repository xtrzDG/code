"""The team's internal notes about a visitor: exported and erased with them."""

from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from app.schemas.typings.users.prefixed_id import UserId
from tests.compliance.two_tenants import TwoTenants, command, seed_two_tenants


def write_note(
    tenants: TwoTenants,
    conversation: ConversationDocument,
    author_user_id: UserId,
    text: str,
) -> ConversationNoteDocument:
    tenants.testbed.clock.advance(1)
    now = tenants.testbed.clock.now_microseconds()
    note = ConversationNoteDocument(
        business_id=conversation.business_id,
        conversation_id=conversation.id,
        author_user_id=author_user_id,
        text=ConversationNoteText(text),
        created_at=now,
        updated_at=now,
    )
    tenants.testbed.conversation_note_repo.add(note)
    return note


def test_export_holds_the_notes_on_the_visitor_conversations_oldest_first() -> None:
    tenants = seed_two_tenants()
    visitor = tenants.visitor
    first = write_note(
        tenants, visitor.chat_conversation, tenants.owner_id, "Prefers the window"
    )
    second = write_note(
        tenants, visitor.phone_conversation, tenants.staff_id, "Called twice"
    )
    write_note(
        tenants, tenants.neighbour.chat_conversation, tenants.owner_id, "Other guest"
    )

    export = tenants.testbed.export_contact_data.run(
        command(tenants, visitor.contact.id)
    )

    assert [note.id for note in export.records.notes] == [first.id, second.id]
    assert "Other guest" not in export.model_dump_json()


def test_erasure_deletes_the_visitor_notes_and_keeps_everyone_else() -> None:
    tenants = seed_two_tenants()
    visitor = tenants.visitor
    notes_repo = tenants.testbed.conversation_note_repo
    for conversation in (visitor.chat_conversation, visitor.phone_conversation):
        write_note(tenants, conversation, tenants.owner_id, "Allergic to nuts")
    kept = write_note(
        tenants, tenants.neighbour.chat_conversation, tenants.staff_id, "Regular"
    )

    result = tenants.testbed.delete_contact_data.run(
        command(tenants, visitor.contact.id)
    )

    assert result.deleted_notes == 2
    for conversation in (visitor.chat_conversation, visitor.phone_conversation):
        assert (
            notes_repo.list_by_conversation(tenants.business.id, conversation.id) == []
        )
    assert notes_repo.get(tenants.business.id, kept.id) == kept
