"""Assigning conversations: compare and set, and the owner/staff rules."""

import threading

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.assignment import (
    AssignConversationCommand,
    ConversationAssignmentView,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from app.schemas.typings.users.prefixed_id import UserId
from tests.inbox.inbox_builders import hand_off, reload, talk
from tests.inbox.inbox_world import InboxWorld


def command(
    world: InboxWorld,
    conversation: ConversationDocument,
    caller: UserId,
    assignee: UserId | None,
    revision: int = 0,
) -> AssignConversationCommand:
    return AssignConversationCommand(
        user_id=caller,
        business_id=world.business.id,
        conversation_id=conversation.id,
        assignee_user_id=assignee,
        expected_revision=AssignmentRevision(revision),
    )


def waiting(world: InboxWorld) -> ConversationDocument:
    conversation = talk(world, "Nino", minutes_ago=4)
    hand_off(world, conversation)
    return conversation


def reason_codes(error: ApplicationError) -> list[str]:
    return [str(reason.code) for reason in error.reasons]


def test_the_owner_assigns_and_the_change_is_audited_and_announced() -> None:
    world = InboxWorld()
    conversation = waiting(world)

    view = world.assign().run(
        command(world, conversation, world.owner.id, world.staff.id)
    )

    assert view == ConversationAssignmentView(
        conversation_id=conversation.id,
        assignee_user_id=world.staff.id,
        assigned_by=world.owner.id,
        assigned_at=world.now,
        assignment_revision=AssignmentRevision(1),
    )
    entry = world.audit_entries()[-1]
    assert (entry.action, str(entry.entity), str(entry.entity_id)) == (
        AuditAction.UPDATE,
        "conversation_assignment",
        str(conversation.id),
    )
    assert entry.actor_id == world.owner.id
    event = world.live_events.events[-1]
    assert event.event is LiveEventKind.CONVERSATION_ASSIGNED
    assert event.ids == (str(conversation.id), str(world.staff.id))


def test_staff_take_an_unassigned_conversation_and_pass_on_their_own() -> None:
    world = InboxWorld()
    conversation = waiting(world)
    assign = world.assign()

    taken = assign.run(command(world, conversation, world.staff.id, world.staff.id))
    passed = assign.run(
        command(world, conversation, world.staff.id, world.colleague.id, revision=1)
    )

    assert taken.assignee_user_id == world.staff.id
    assert passed.assignee_user_id == world.colleague.id
    assert passed.assigned_by == world.staff.id
    assert passed.assignment_revision == AssignmentRevision(2)


def test_staff_cannot_take_a_colleagues_conversation_but_the_owner_can() -> None:
    world = InboxWorld()
    conversation = waiting(world)
    assign = world.assign()
    assign.run(command(world, conversation, world.owner.id, world.colleague.id))

    with pytest.raises(AccessDeniedError) as refused:
        assign.run(command(world, conversation, world.staff.id, world.staff.id, 1))
    with pytest.raises(AccessDeniedError):
        assign.run(command(world, conversation, world.staff.id, None, 1))

    assert reason_codes(refused.value) == ["assigned_to_colleague"]
    moved = assign.run(command(world, conversation, world.owner.id, world.staff.id, 1))
    assert moved.assignee_user_id == world.staff.id


def test_a_revision_that_moved_on_is_refused_with_a_conflict() -> None:
    world = InboxWorld()
    conversation = waiting(world)
    assign = world.assign()
    assign.run(command(world, conversation, world.owner.id, world.staff.id))

    with pytest.raises(ConflictError) as refused:
        assign.run(command(world, conversation, world.owner.id, world.colleague.id))

    assert reason_codes(refused.value) == ["assignment_changed"]
    assert reload(world, conversation).assignee_user_id == world.staff.id


def test_only_members_can_be_assigned() -> None:
    world = InboxWorld()
    conversation = waiting(world)

    with pytest.raises(ValidationFailedError) as refused:
        world.assign().run(
            command(world, conversation, world.owner.id, world.stranger.id)
        )

    assert reason_codes(refused.value) == ["not_a_member"]


def test_strangers_and_test_chats_are_refused() -> None:
    world = InboxWorld()
    conversation = waiting(world)
    test_chat = talk(world, "Owner", minutes_ago=2, is_sandbox=True)

    with pytest.raises(NotFoundError):
        world.assign().run(
            command(world, conversation, world.stranger.id, world.stranger.id)
        )
    with pytest.raises(ValidationFailedError):
        world.assign().run(command(world, test_chat, world.owner.id, world.staff.id))
    with pytest.raises(NotFoundError):
        world.assign().run(
            command(world, talk(InboxWorld(), "X", 1), world.owner.id, None)
        )


def test_the_same_assignee_again_changes_nothing() -> None:
    world = InboxWorld()
    conversation = waiting(world)
    assign = world.assign()
    assign.run(command(world, conversation, world.owner.id, world.staff.id))
    events = len(world.live_events.events)

    again = assign.run(command(world, conversation, world.staff.id, world.staff.id, 1))

    assert again.assignment_revision == AssignmentRevision(1)
    assert len(world.live_events.events) == events


def test_of_two_people_taking_a_conversation_at_once_exactly_one_wins() -> None:
    world = InboxWorld()
    conversation = waiting(world)
    takers = (world.staff.id, world.colleague.id)
    start = threading.Barrier(len(takers))
    outcomes: dict[str, str] = {}

    def take(user_id: UserId) -> None:
        use_case = world.assign()
        start.wait()
        try:
            use_case.run(command(world, conversation, user_id, user_id))
            outcomes[str(user_id)] = "won"
        except ConflictError:
            outcomes[str(user_id)] = "conflict"

    threads = [threading.Thread(target=take, args=(user_id,)) for user_id in takers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes.values()) == ["conflict", "won"]
    winner = next(user for user, outcome in outcomes.items() if outcome == "won")
    stored = reload(world, conversation)
    assert str(stored.assignee_user_id) == winner
    assert stored.assignment_revision == AssignmentRevision(1)


class RacingConversations:
    """
    The conversation repository, but another member assigns the
    conversation right after the caller read it: the caller's write must
    lose (the compare-and-set of the repository, not the use case's check).
    """

    def __init__(self, world: InboxWorld, rival: UserId) -> None:
        self._world: InboxWorld = world
        self._rival: UserId = rival
        self.inner = world.conversation_repo

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name)

    def get(self, business_id: object, conversation_id: object) -> object:
        read = self.inner.get(business_id, conversation_id)  # type: ignore[arg-type]
        rival_view = self._world.assign().run(
            command(self._world, read, self._rival, self._rival)  # type: ignore[arg-type]
        )
        assert rival_view.assignee_user_id == self._rival
        return read


def test_a_write_that_loses_the_race_after_the_read_is_a_conflict() -> None:
    world = InboxWorld()
    conversation = waiting(world)
    use_case = world.assign()
    use_case._conversation_repo = RacingConversations(  # type: ignore[assignment]
        world, world.colleague.id
    )

    with pytest.raises(ConflictError):
        use_case.run(command(world, conversation, world.staff.id, world.staff.id))

    assert reload(world, conversation).assignee_user_id == world.colleague.id
