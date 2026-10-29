"""A busy morning in the restaurant's inbox, shared by the view tests."""

from dataclasses import dataclass

from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.assignment import ConversationAssignmentChange
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from app.schemas.typings.users.prefixed_id import UserId
from tests.inbox.inbox_builders import hand_off, request, talk
from tests.inbox.inbox_world import InboxWorld


@dataclass
class InboxScene:
    """
    Conversations of every kind, newest first by name:
    - mine_handoff: needs a person, assigned to Giorgi (staff)
    - ana_request: an open request, assigned to Ana
    - unassigned_handoff: needs a person, nobody assigned
    - unassigned_request: an open request (in progress), nobody assigned
    - both: needs a person and has an open request, nobody assigned
    - won_request: its request was won, assigned to Giorgi (no longer waits)
    - quiet: the assistant handled it alone
    - test_chat: the owner's test chat that needs a person (never listed)
    """

    world: InboxWorld
    mine_handoff: ConversationDocument
    ana_request: ConversationDocument
    unassigned_handoff: ConversationDocument
    unassigned_request: ConversationDocument
    both: ConversationDocument
    won_request: ConversationDocument
    quiet: ConversationDocument
    test_chat: ConversationDocument


def assign(world: InboxWorld, conversation: ConversationDocument, to: UserId) -> None:
    stored = world.conversation_repo.get(world.business.id, conversation.id)
    assert stored is not None
    world.conversation_repo.assign(
        world.business.id,
        conversation.id,
        ConversationAssignmentChange(
            assignee_user_id=to,
            assigned_by=world.owner.id,
            expected_revision=AssignmentRevision(int(stored.assignment_revision)),
            at=world.now,
        ),
    )


def build_scene(world: InboxWorld | None = None) -> InboxScene:
    world = InboxWorld() if world is None else world
    mine_handoff = talk(world, "Nino", minutes_ago=1)
    hand_off(world, mine_handoff)
    assign(world, mine_handoff, world.staff.id)
    ana_request = talk(world, "Dato", minutes_ago=2, channel=ChannelKind.WHATSAPP)
    request(world, ana_request)
    assign(world, ana_request, world.colleague.id)
    unassigned_handoff = talk(world, "Mariam", minutes_ago=3)
    hand_off(world, unassigned_handoff)
    unassigned_request = talk(world, "Irakli", minutes_ago=4)
    request(world, unassigned_request, LeadStatus.IN_PROGRESS)
    both = talk(world, "Tamar", minutes_ago=5, channel=ChannelKind.WHATSAPP)
    hand_off(world, both)
    request(world, both)
    won_request = talk(world, "Saba", minutes_ago=6)
    request(world, won_request, LeadStatus.WON)
    assign(world, won_request, world.staff.id)
    quiet = talk(world, "Eka", minutes_ago=7)
    test_chat = talk(world, "Owner", minutes_ago=0, is_sandbox=True)
    hand_off(world, test_chat)
    return InboxScene(
        world=world,
        mine_handoff=mine_handoff,
        ana_request=ana_request,
        unassigned_handoff=unassigned_handoff,
        unassigned_request=unassigned_request,
        both=both,
        won_request=won_request,
        quiet=quiet,
        test_chat=test_chat,
    )
