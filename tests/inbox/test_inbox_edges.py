"""Edges of the team inbox: races, empty reads and what a row leaves out."""

import pytest

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.inbox.assignment import ConversationAssignmentChange
from app.schemas.dto.inbox.inbox_views import InboxItemSource
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from app.schemas.typings.inbox.prefixed_id import QuickReplyId
from app.schemas.typings.users.prefixed_id import UserId
from app.transformers.inbox.inbox_item_transformer import InboxItemTransformer
from tests.inbox.inbox_builders import reload
from tests.inbox.inbox_world import InboxWorld
from tests.inbox.quick_reply_steps import reply_request, save
from tests.inbox.test_auto_assign import auto_assign, new_handoff, turn_on


class AssignedMeanwhile:
    """
    The conversation repository, but a colleague takes the conversation
    right after the automatic assignment read it.
    """

    def __init__(self, world: InboxWorld, colleague: UserId) -> None:
        self._world: InboxWorld = world
        self._colleague: UserId = colleague
        self.inner = world.conversation_repo

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name)

    def get(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> ConversationDocument | None:
        read = self.inner.get(business_id, conversation_id)
        assert read is not None
        taken = self.inner.assign(
            business_id,
            conversation_id,
            ConversationAssignmentChange(
                assignee_user_id=self._colleague,
                assigned_by=self._colleague,
                expected_revision=AssignmentRevision(int(read.assignment_revision)),
                at=self._world.now,
            ),
        )
        assert taken is not None
        return read


def test_an_automatic_assignment_yields_to_a_person_who_was_quicker() -> None:
    world = InboxWorld()
    turn_on(world)
    conversation = new_handoff(world)
    use_case = world.auto_assign()
    use_case._conversation_repo = AssignedMeanwhile(  # type: ignore[assignment]
        world, world.colleague.id
    )
    world.auto_assign = lambda: use_case  # type: ignore[method-assign]

    result = auto_assign(world, conversation)

    assert result.assignment is None
    assert reload(world, conversation).assignee_user_id == world.colleague.id


def test_a_row_never_previews_a_system_message() -> None:
    world = InboxWorld()
    conversation = new_handoff(world)
    system_message = MessageDocument(
        conversation_id=conversation.id,
        business_id=world.business.id,
        direction=MessageDirection.OUTBOUND,
        author=MessageAuthor.SYSTEM,
        text=MessageText("The conversation was handed to a person."),
        created_at=world.now,
        updated_at=world.now,
    )

    row = InboxItemTransformer().transform(
        InboxItemSource(conversation=conversation, last_written=system_message)
    )

    assert (row.last_message_text, row.last_message_author) == (None, None)


def test_note_counts_of_no_conversations_are_empty() -> None:
    world = InboxWorld()

    assert world.note_repo.count_by_conversations(world.business.id, []) == {}


def test_replacing_a_saved_reply_that_is_gone_is_not_found() -> None:
    world = InboxWorld()

    with pytest.raises(NotFoundError, match="was not found"):
        save(world, reply_request(), replacing=QuickReplyId())
