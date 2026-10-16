"""Automatic assignment of new handoffs and requests."""

from app.schemas.constants.inbox import InboxView
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.dto.inbox.assignment import AutoAssignCommand, AutoAssignResult
from app.schemas.typings.users.prefixed_id import UserId
from tests.inbox.inbox_builders import hand_off, reload, talk
from tests.inbox.inbox_scene import assign
from tests.inbox.inbox_world import InboxWorld


def turn_on(
    world: InboxWorld,
    handoffs: bool = True,
    requests: bool = False,
    members: list[UserId] | None = None,
) -> None:
    def change(settings: InboxSettingsDocument) -> None:
        settings.auto_assign_new_handoffs = handoffs
        settings.auto_assign_new_requests = requests
        settings.auto_assign_user_ids = members or []

    world.settings_repo.change(world.business.id, change, world.now)


def new_handoff(world: InboxWorld, minutes_ago: int = 1) -> ConversationDocument:
    conversation = talk(world, f"Guest {minutes_ago}", minutes_ago=minutes_ago)
    hand_off(world, conversation)
    return conversation


def auto_assign(
    world: InboxWorld,
    conversation: ConversationDocument,
    trigger: InboxView = InboxView.NEEDS_PERSON,
) -> AutoAssignResult:
    return world.auto_assign().run(
        AutoAssignCommand(
            business_id=world.business.id,
            conversation_id=conversation.id,
            trigger=trigger,
            is_sandbox=conversation.is_sandbox,
        )
    )


def assignee(world: InboxWorld, conversation: ConversationDocument) -> UserId | None:
    return reload(world, conversation).assignee_user_id


def test_nothing_is_assigned_unless_the_business_asks_for_it() -> None:
    world = InboxWorld()
    conversation = new_handoff(world)

    assert auto_assign(world, conversation).assignment is None
    turn_on(world, handoffs=False, requests=True)
    assert auto_assign(world, conversation).assignment is None
    assert assignee(world, conversation) is None


def test_a_new_handoff_goes_to_the_staff_member_with_the_least_work() -> None:
    world = InboxWorld()
    turn_on(world)
    busy = new_handoff(world, minutes_ago=9)
    assign(world, busy, world.staff.id)
    conversation = new_handoff(world)

    result = auto_assign(world, conversation)

    assert result.assignment is not None
    assert result.assignment.assignee_user_id == world.colleague.id
    assert result.assignment.is_assigned_automatically is True
    stored = reload(world, conversation)
    assert (stored.assignee_user_id, stored.assigned_by) == (world.colleague.id, None)
    event = world.live_events.events[-1]
    assert event.event is LiveEventKind.CONVERSATION_ASSIGNED
    entry = world.audit_entries()[-1]
    assert (entry.actor_id, str(entry.entity)) == (None, "conversation_assignment")


def test_equally_busy_members_take_turns() -> None:
    world = InboxWorld()
    turn_on(world)

    first = new_handoff(world, minutes_ago=3)
    auto_assign(world, first)
    # Their work is done: both are free again.
    for done in (first,):
        stored = reload(world, done)
        stored.status = stored.status.OPEN
        world.conversation_repo.save(stored)
    second = new_handoff(world, minutes_ago=2)
    auto_assign(world, second)

    assert assignee(world, first) == world.staff.id
    assert assignee(world, second) == world.colleague.id


def test_only_the_chosen_members_take_new_work() -> None:
    world = InboxWorld()
    turn_on(world, members=[world.colleague.id, world.stranger.id])

    conversation = new_handoff(world)
    auto_assign(world, conversation)

    assert assignee(world, conversation) == world.colleague.id


def test_a_business_without_staff_gives_new_work_to_its_owner() -> None:
    world = InboxWorld()
    world.business.members = [
        BusinessMember(user_id=world.owner.id, role=BusinessMemberRole.OWNER)
    ]
    world.business_repo.save(world.business)
    turn_on(world)

    conversation = new_handoff(world)
    auto_assign(world, conversation)

    assert assignee(world, conversation) == world.owner.id


def test_new_requests_are_assigned_when_asked_for() -> None:
    world = InboxWorld()
    turn_on(world, handoffs=False, requests=True)
    conversation = talk(world, "Dato", minutes_ago=1)

    auto_assign(world, conversation, InboxView.REQUESTS)

    assert assignee(world, conversation) == world.staff.id


def test_an_assigned_conversation_keeps_its_person() -> None:
    world = InboxWorld()
    turn_on(world)
    conversation = new_handoff(world)
    assign(world, conversation, world.owner.id)

    assert auto_assign(world, conversation).assignment is None
    assert assignee(world, conversation) == world.owner.id


def test_test_chats_and_missing_conversations_are_never_assigned() -> None:
    world = InboxWorld()
    turn_on(world)
    test_chat = talk(world, "Owner", minutes_ago=1, is_sandbox=True)
    hand_off(world, test_chat)
    elsewhere = talk(InboxWorld(), "Guest", minutes_ago=1)

    assert auto_assign(world, test_chat).assignment is None
    assert auto_assign(world, elsewhere).assignment is None
    assert (
        world.auto_assign()
        .run(
            AutoAssignCommand(
                business_id=world.business.id,
                conversation_id=test_chat.id,
                trigger=InboxView.NEEDS_PERSON,
                is_sandbox=False,
            )
        )
        .assignment
        is None
    )


def test_other_triggers_never_assign() -> None:
    world = InboxWorld()
    turn_on(world, handoffs=True, requests=True)

    assert auto_assign(world, new_handoff(world), InboxView.ALL).assignment is None


def test_a_business_with_nobody_to_choose_assigns_nobody() -> None:
    world = InboxWorld()
    turn_on(world, members=[world.stranger.id])

    conversation = new_handoff(world)

    assert auto_assign(world, conversation).assignment is None
