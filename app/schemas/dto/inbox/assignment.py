"""Assigning a conversation of the team inbox to a member (compare and set)."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.inbox import InboxView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.booleans import (
    HasOpenRequest,
    IsAssignedAutomatically,
)
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from app.schemas.typings.users.prefixed_id import UserId


class AssignConversationRequest(ImmutableDTO):
    """
    Body of POST .../conversations/{conversation_id}/assign: the member to
    assign (null: nobody) and the `assignment_revision` the caller saw. A
    revision that is no longer current is refused with 409
    (`assignment_changed`): someone else changed the assignment meanwhile.
    """

    assignee_user_id: UserId | None = None
    expected_revision: AssignmentRevision


class AssignConversationCommand(ImmutableDTO):
    """A member assigns a conversation (owners any; staff see the router)."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    assignee_user_id: UserId | None = None
    expected_revision: AssignmentRevision
    client_ip_address: ClientIpAddress | None = None


class ConversationAssignmentChange(ImmutableDTO):
    """
    What the repository writes when the stored revision still is
    `expected_revision`: the new assignee (None: nobody), who assigned it
    (None: the automatic assignment) and when.
    """

    assignee_user_id: UserId | None = None
    assigned_by: UserId | None = None
    expected_revision: AssignmentRevision
    at: Microseconds


class ConversationAssignmentView(ImmutableDTO):
    """The assignment of a conversation after a change."""

    conversation_id: ConversationId
    assignee_user_id: UserId | None = None
    assigned_by: UserId | None = None
    assigned_at: Microseconds | None = None
    is_assigned_automatically: IsAssignedAutomatically = False
    assignment_revision: AssignmentRevision


class AutoAssignCommand(ImmutableDTO):
    """
    New work arrived in a conversation (`trigger`: NEEDS_PERSON for a new
    handoff, REQUESTS for a new request): assign it automatically when the
    business asks for that and nobody is assigned yet.
    """

    business_id: BusinessId
    conversation_id: ConversationId
    trigger: InboxView
    is_sandbox: IsSandboxConversation = False


class AutoAssignResult(ImmutableDTO):
    """The automatic assignment made, None when nobody was assigned."""

    assignment: ConversationAssignmentView | None = None


class OpenRequestRefresh(ImmutableDTO):
    """
    A request of a conversation was made or changed: recount whether the
    conversation has an open request (new or in progress).
    """

    business_id: BusinessId
    conversation_id: ConversationId


class OpenRequestState(ImmutableDTO):
    """Whether a conversation has an open request after a recount."""

    conversation_id: ConversationId
    has_open_request: HasOpenRequest
