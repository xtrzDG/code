"""The team behind the inbox: who can be assigned, and the inbox settings."""

import logging

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffStatus,
    HandoffUrgency,
)
from app.schemas.constants.inbox import InboxView
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.inbox.assignment import AutoAssignCommand, AutoAssignResult
from app.schemas.dto.inbox.inbox_settings import (
    InboxSettingsQuery,
    InboxSettingsRequest,
    UpdateInboxSettingsCommand,
)
from app.schemas.dto.inbox.inbox_views import InboxAssigneesQuery
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.inbox.constrained_integers import AwaitingConversationCount
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.inbox.assignment.auto_assigning_handoff_use_case import (
    AutoAssigningHandoffUseCase,
)
from tests.inbox.inbox_builders import hand_off, talk
from tests.inbox.inbox_scene import assign
from tests.inbox.inbox_world import InboxWorld


def test_assignees_are_the_members_owners_first_with_their_work() -> None:
    world = InboxWorld()
    for minutes in (3, 2):
        conversation = talk(world, f"Guest {minutes}", minutes_ago=minutes)
        hand_off(world, conversation)
        assign(world, conversation, world.colleague.id)

    assignees = world.list_assignees().run(
        InboxAssigneesQuery(user_id=world.staff.id, business_id=world.business.id)
    )

    assert [
        (str(item.display_name), item.role, item.awaiting_count)
        for item in assignees.items
    ] == [
        ("Nino", BusinessMemberRole.OWNER, AwaitingConversationCount(0)),
        ("Ana", BusinessMemberRole.STAFF, AwaitingConversationCount(2)),
        ("Giorgi", BusinessMemberRole.STAFF, AwaitingConversationCount(0)),
    ]


def settings_command(
    world: InboxWorld, caller: UserId, members: list[UserId]
) -> UpdateInboxSettingsCommand:
    return UpdateInboxSettingsCommand(
        user_id=caller,
        business_id=world.business.id,
        request=InboxSettingsRequest(
            auto_assign_new_handoffs=True, auto_assign_user_ids=members
        ),
    )


def test_owners_turn_auto_assignment_on_and_the_team_reads_it() -> None:
    world = InboxWorld()
    query = InboxSettingsQuery(user_id=world.staff.id, business_id=world.business.id)
    assert world.get_settings().run(query).auto_assign_new_handoffs is False

    world.update_settings().run(
        settings_command(
            world, world.owner.id, [world.staff.id, world.staff.id, world.owner.id]
        )
    )

    settings = world.get_settings().run(query)
    assert settings.auto_assign_new_handoffs is True
    assert settings.auto_assign_new_requests is False
    assert settings.auto_assign_user_ids == [world.staff.id, world.owner.id]
    entry = world.audit_entries()[-1]
    assert (entry.action, str(entry.entity)) == (AuditAction.UPDATE, "inbox_settings")


def test_only_owners_change_settings_and_only_for_members() -> None:
    world = InboxWorld()

    with pytest.raises(AccessDeniedError):
        world.update_settings().run(settings_command(world, world.staff.id, []))
    with pytest.raises(ValidationFailedError):
        world.update_settings().run(
            settings_command(world, world.owner.id, [world.stranger.id])
        )


class OpenedHandoff:
    """The handoff use case, standing in: the handoff is always stored."""

    def __init__(self, world: InboxWorld) -> None:
        self._world = world

    def run(self, input_data: HandoffCommand) -> HandoffResult:
        return HandoffResult(
            id=HandoffId(),
            business_id=input_data.business_id,
            conversation_id=input_data.conversation_id,
            reason=input_data.reason,
            urgency=input_data.urgency,
            status=HandoffStatus.PENDING,
            customer_message=MessageText("A colleague will reply soon."),
        )


class FailingAutoAssign:
    def run(self, input_data: AutoAssignCommand) -> AutoAssignResult:
        raise ExternalServiceError(f"No storage for {input_data.conversation_id}.")


class RecordingAutoAssign:
    def __init__(self) -> None:
        self.commands: list[AutoAssignCommand] = []

    def run(self, input_data: AutoAssignCommand) -> AutoAssignResult:
        self.commands.append(input_data)
        return AutoAssignResult()


def handoff_command(world: InboxWorld) -> HandoffCommand:
    conversation = talk(world, "Nino", minutes_ago=1)
    return HandoffCommand.model_validate(
        {
            "business_id": world.business.id,
            "conversation_id": conversation.id,
            "contact_id": conversation.contact_id,
            "reason": HandoffReason.CUSTOMER_REQUEST,
            "summary": "Wants a person.",
            "urgency": HandoffUrgency.NORMAL,
            "language": "ka",
            "source_channel": conversation.channel,
        }
    )


def test_every_new_handoff_asks_the_inbox_for_an_assignee() -> None:
    world = InboxWorld()
    assigner = RecordingAutoAssign()
    command = handoff_command(world)

    result = AutoAssigningHandoffUseCase(OpenedHandoff(world), assigner).run(command)

    assert [(c.conversation_id, c.trigger) for c in assigner.commands] == [
        (result.conversation_id, InboxView.NEEDS_PERSON)
    ]


def test_a_failed_assignment_never_fails_the_handoff(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = InboxWorld()

    with caplog.at_level(logging.ERROR):
        result = AutoAssigningHandoffUseCase(
            OpenedHandoff(world), FailingAutoAssign()
        ).run(handoff_command(world))

    assert str(result.customer_message) == "A colleague will reply soon."
    assert "could not be assigned automatically" in caplog.text
