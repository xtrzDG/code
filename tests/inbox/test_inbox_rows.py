"""The staff-safe row of a conversation in the team inbox."""

from typing import cast

from app.schemas.constants.bookings import LeadStatus, LeadType
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.handoffs import HandoffUrgency
from app.schemas.constants.inbox import InboxView
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.inbox.assignment import ConversationAssignmentChange
from app.schemas.dto.inbox.inbox_views import InboxItemView, InboxPage, InboxQuery
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.inbox.constrained_integers import (
    AssignmentRevision,
    ConversationNoteCount,
)
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from tests.inbox.inbox_builders import hand_off, request, talk
from tests.inbox.inbox_world import InboxWorld

# What a staff member must never read in the list: the model's internals,
# the cost, and free texts of requests and handoffs.
PRIVATE_KEYS: frozenset[str] = frozenset(
    {
        "assistant_version_id",
        "cost_micro_usd",
        "model_id",
        "tool_calls",
        "input_tokens",
        "details",
        "budget",
        "summary",
        "is_sandbox",
        "text",
    }
)


def list_all(world: InboxWorld, view: InboxView = InboxView.ALL) -> InboxPage:
    return world.list_inbox().run(
        InboxQuery(user_id=world.staff.id, business_id=world.business.id, view=view)
    )


def only_row(world: InboxWorld) -> InboxItemView:
    items = list_all(world).items
    assert len(items) == 1
    return items[0]


def test_a_row_shows_the_customer_the_work_and_who_has_it() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3, text="Can I bring my dog?")
    handoff = hand_off(world, conversation, HandoffUrgency.HIGH)
    lead = request(world, conversation, LeadStatus.IN_PROGRESS)
    for text in ("Called her back.", "Prefers the terrace."):
        world.note_repo.add(
            ConversationNoteDocument(
                business_id=world.business.id,
                conversation_id=conversation.id,
                author_user_id=world.owner.id,
                text=ConversationNoteText(text),
            )
        )

    row = only_row(world)

    assert (row.contact_name, row.contact_phone_number) == ("Nino", "+995555123456")
    assert (row.needs_person, row.has_open_request, row.awaits_team) == (
        True,
        True,
        True,
    )
    assert row.handoff is not None and row.handoff.id == handoff.id
    assert row.handoff.urgency is HandoffUrgency.HIGH
    assert row.request is not None and row.request.id == lead.id
    assert (row.request.lead_type, row.request.status) == (
        LeadType.BANQUET,
        LeadStatus.IN_PROGRESS,
    )
    assert row.note_count == ConversationNoteCount(2)
    assert str(row.last_message_text) == "Can I bring my dog?"
    assert row.last_message_author is MessageAuthor.CUSTOMER
    assert row.assignee_user_id is None
    assert row.assignment_revision == AssignmentRevision(0)


def test_a_row_says_when_the_inbox_assigned_it_automatically() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3)
    world.conversation_repo.assign(
        world.business.id,
        conversation.id,
        ConversationAssignmentChange(
            assignee_user_id=world.staff.id,
            expected_revision=AssignmentRevision(0),
            at=world.now,
        ),
    )

    row = only_row(world)

    assert row.assignee_user_id == world.staff.id
    assert row.is_assigned_automatically is True
    assert row.assigned_at == world.now


def test_a_system_note_is_never_the_preview() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3)
    world.message_repo.save(
        MessageDocument(
            conversation_id=conversation.id,
            business_id=world.business.id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.SYSTEM,
            text=MessageText("Voice agent called check_availability."),
            created_at=world.later(1),
            updated_at=world.now,
        )
    )

    row = only_row(world)

    assert str(row.last_message_text) == "Hello, is there a table for tonight?"
    assert row.last_message_author is MessageAuthor.CUSTOMER


def test_rows_keep_model_details_and_free_texts_out() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=3)
    hand_off(world, conversation)
    request(world, conversation)

    keys: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            fields = cast(dict[str, object], value)
            keys.update(fields)
            for inner in fields.values():
                collect(inner)
        elif isinstance(value, list):
            for inner in cast(list[object], value):
                collect(inner)

    collect(list_all(world).model_dump(mode="json"))

    assert keys & PRIVATE_KEYS == set()


def test_a_page_without_conversations_is_empty_with_zero_counts() -> None:
    world = InboxWorld()

    result = list_all(world, InboxView.NEEDS_PERSON)

    assert result.items == [] and result.next_cursor is None
    assert result.counts.needs_person == 0
