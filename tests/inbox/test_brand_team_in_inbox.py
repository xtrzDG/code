"""
A brand's team works in the inbox of its locations with the role it acts
with there: a brand owner as an owner (takes over a colleague's
conversation, deletes any note), a regional manager as staff (can be
assigned, and chosen for automatic assignment); the location's own team
still takes turns when nobody was chosen.
"""

import pytest

from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.inbox import InboxView
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.inbox.assignment import (
    AssignConversationCommand,
    AutoAssignCommand,
)
from app.schemas.dto.inbox.conversation_notes import (
    CreateConversationNoteCommand,
    DeleteConversationNoteCommand,
)
from app.schemas.dto.inbox.inbox_settings import (
    InboxSettingsRequest,
    UpdateInboxSettingsCommand,
)
from app.schemas.dto.inbox.inbox_views import InboxAssigneesQuery
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from app.schemas.typings.users.prefixed_id import UserId
from tests.inbox.inbox_builders import hand_off, reload, talk
from tests.inbox.inbox_scene import assign
from tests.inbox.inbox_store import build_user
from tests.inbox.inbox_world import InboxWorld


class BrandInbox:
    """The inbox world's business as a location of a brand: Levan owns the
    brand (no member of the location), Tamar manages the location."""

    def __init__(self, in_brand: bool = True) -> None:
        self.world = InboxWorld()
        self.brand_owner: UserDocument = self.world.stranger
        self.manager: UserDocument = build_user("Tamar")
        self.world.user_repo.save(self.manager)
        brand = BrandDocument(
            name=BrandName("Mtsvane Ezo"),
            members=[
                BrandMember(
                    user_id=self.brand_owner.id, role=BrandMemberRole.BRAND_OWNER
                ),
                BrandMember(
                    user_id=self.manager.id,
                    role=BrandMemberRole.REGIONAL_MANAGER,
                    business_ids=[self.world.business.id],
                ),
            ],
        )
        self.world.brand_repo.add(brand)
        if in_brand:
            self.world.business.brand_id = brand.id
            self.world.business_repo.save(self.world.business)

    def assign(
        self, conversation: ConversationDocument, caller: UserId, to: UserId
    ) -> None:
        self.world.assign().run(
            AssignConversationCommand(
                user_id=caller,
                business_id=self.world.business.id,
                conversation_id=conversation.id,
                assignee_user_id=to,
                expected_revision=reload(self.world, conversation).assignment_revision,
            )
        )


def waiting(world: InboxWorld, name: str = "Nino") -> ConversationDocument:
    conversation = talk(world, name, minutes_ago=4)
    hand_off(world, conversation)
    return conversation


def auto_assign(world: InboxWorld, conversation: ConversationDocument) -> None:
    world.auto_assign().run(
        AutoAssignCommand(
            business_id=world.business.id,
            conversation_id=conversation.id,
            trigger=InboxView.NEEDS_PERSON,
            is_sandbox=conversation.is_sandbox,
        )
    )


def turn_on(brand: BrandInbox, chosen: list[UserId]) -> None:
    world = brand.world
    world.update_settings().run(
        UpdateInboxSettingsCommand(
            user_id=brand.brand_owner.id,
            business_id=world.business.id,
            request=InboxSettingsRequest(
                auto_assign_new_handoffs=True,
                auto_assign_user_ids=chosen,
            ),
        )
    )


def test_a_brand_owner_takes_over_a_colleagues_conversation() -> None:
    brand = BrandInbox()
    conversation = waiting(brand.world)
    assign(brand.world, conversation, brand.world.staff.id)

    brand.assign(conversation, brand.brand_owner.id, brand.brand_owner.id)

    assert reload(brand.world, conversation).assignee_user_id == brand.brand_owner.id


def test_a_regional_manager_can_be_assigned_by_the_owner() -> None:
    brand = BrandInbox()
    conversation = waiting(brand.world)

    brand.assign(conversation, brand.world.owner.id, brand.manager.id)

    assert reload(brand.world, conversation).assignee_user_id == brand.manager.id


def test_people_of_a_brand_the_location_left_cannot_be_assigned() -> None:
    brand = BrandInbox(in_brand=False)
    conversation = waiting(brand.world)

    with pytest.raises(ValidationFailedError):
        brand.assign(conversation, brand.world.owner.id, brand.manager.id)


def test_the_assignees_list_the_brand_team_with_the_role_they_act_with() -> None:
    brand = BrandInbox()

    roles = {
        assignee.user_id: assignee.role
        for assignee in brand.world.list_assignees()
        .run(
            InboxAssigneesQuery(
                user_id=brand.manager.id, business_id=brand.world.business.id
            )
        )
        .items
    }

    assert roles[brand.brand_owner.id] is BusinessMemberRole.OWNER
    assert roles[brand.manager.id] is BusinessMemberRole.STAFF
    assert roles[brand.world.staff.id] is BusinessMemberRole.STAFF


def test_a_brand_owner_deletes_a_note_of_the_staff() -> None:
    brand = BrandInbox()
    world = brand.world
    conversation = talk(world, "Nino", minutes_ago=4)
    note = world.create_note().run(
        CreateConversationNoteCommand(
            user_id=world.staff.id,
            business_id=world.business.id,
            conversation_id=conversation.id,
            text=ConversationNoteText("Called back, no answer."),
        )
    )

    world.delete_note().run(
        DeleteConversationNoteCommand(
            user_id=brand.brand_owner.id,
            business_id=world.business.id,
            conversation_id=conversation.id,
            note_id=note.id,
        )
    )

    assert world.note_repo.get(world.business.id, note.id) is None


def test_a_chosen_regional_manager_takes_new_handoffs() -> None:
    brand = BrandInbox()
    turn_on(brand, [brand.manager.id])
    conversation = waiting(brand.world, "Guest")

    auto_assign(brand.world, conversation)

    assert reload(brand.world, conversation).assignee_user_id == brand.manager.id


def test_without_a_choice_the_locations_own_staff_take_turns() -> None:
    brand = BrandInbox()
    turn_on(brand, [])
    conversation = waiting(brand.world, "Guest")

    auto_assign(brand.world, conversation)

    assert reload(brand.world, conversation).assignee_user_id in {
        brand.world.staff.id,
        brand.world.colleague.id,
    }
