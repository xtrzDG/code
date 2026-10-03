from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import InboxRefusalCode
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.assignment import (
    AssignConversationCommand,
    ConversationAssignmentChange,
    ConversationAssignmentView,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    ValidationFailedError,
)
from app.use_cases.inbox.assignment.assignment_views import build_assignment_view
from app.use_cases.inbox.inbox_support import (
    ASSIGNMENT_ENTITY,
    append_audit,
    is_owner,
    refusal,
    require_conversation,
    require_members,
)


class AssignConversationUseCase(
    UseCaseContract[AssignConversationCommand, ConversationAssignmentView]
):
    """
    A member assigns a conversation of the team inbox to a member, or to
    nobody, by compare and set: the caller names the `assignment_revision`
    they saw, and a revision that moved on (someone else assigned it
    meanwhile) is refused with 409 `assignment_changed`, so two people
    taking the same conversation at once never both win.

    Access goes through `AuthorizeBusinessAccessUseCase` (members, and
    audited platform admins). Owners change any assignment. Staff (and
    admins, who are not members) take or pass on conversations that are
    unassigned or assigned to them, and release their own; a colleague's
    conversation stays theirs (403 `assigned_to_colleague`) until an owner
    reassigns it. Only members can be assigned (422 `not_a_member`), and
    sandbox conversations are not part of the inbox. The same assignee
    again is answered as it is, without a write. Each change is audited
    and announced (`conversation.assigned`).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationTeamRepoContract,
        audit_log_repo: AuditLogRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AssignConversationCommand) -> ConversationAssignmentView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        conversation: ConversationDocument = require_conversation(
            self._conversation_repo, business.id, input_data.conversation_id
        )
        if conversation.is_sandbox:
            raise ValidationFailedError(
                "Test conversations are not part of the team inbox."
            )

        if input_data.assignee_user_id is not None:
            require_members(business, [input_data.assignee_user_id])

        if conversation.assignment_revision != input_data.expected_revision:
            raise assignment_changed()

        current = conversation.assignee_user_id
        if current not in (None, input_data.user_id) and not is_owner(
            business, input_data.user_id
        ):
            raise AccessDeniedError(
                "Only an owner can take over a colleague's conversation.",
                reasons=[
                    refusal(
                        InboxRefusalCode.ASSIGNED_TO_COLLEAGUE,
                        "Ask the owner to reassign this conversation.",
                    )
                ],
            )

        if current == input_data.assignee_user_id:
            return build_assignment_view(conversation)

        now: Microseconds = self._wall_clock.now_unix()
        changed: ConversationDocument | None = self._conversation_repo.assign(
            business.id,
            conversation.id,
            ConversationAssignmentChange(
                assignee_user_id=input_data.assignee_user_id,
                assigned_by=input_data.user_id,
                expected_revision=input_data.expected_revision,
                at=now,
            ),
        )
        if changed is None:
            # The revision moved on between the read and the write.
            raise assignment_changed()

        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.UPDATE,
            ASSIGNMENT_ENTITY,
            str(changed.id),
            input_data.client_ip_address,
            now,
        )
        self._live_events.publish(
            business.id,
            LiveEventKind.CONVERSATION_ASSIGNED,
            (changed.id,)
            if changed.assignee_user_id is None
            else (changed.id, changed.assignee_user_id),
        )
        return build_assignment_view(changed)


def assignment_changed() -> ConflictError:
    return ConflictError(
        "Someone changed the assignment of this conversation meanwhile.",
        reasons=[
            refusal(
                InboxRefusalCode.ASSIGNMENT_CHANGED,
                "Reload the conversation and try again.",
            )
        ],
    )
