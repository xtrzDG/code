from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
    InboxSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import InboxView
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.dto.inbox.assignment import (
    AutoAssignCommand,
    AutoAssignResult,
    ConversationAssignmentChange,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.inbox.inbox_support import ASSIGNMENT_ENTITY, append_audit
from app.use_cases.shared.assignment_views import build_assignment_view
from app.utilities.inbox.auto_assignment import auto_assign_candidates, pick_assignee


class AutoAssignConversationUseCase(
    UseCaseContract[AutoAssignCommand, AutoAssignResult]
):
    """
    New work arrived in a conversation (a handoff, or a request): when the
    business turned auto-assignment on for that kind of work and nobody is
    assigned yet, assign the member with the fewest conversations waiting
    for them (ties take turns, `auto_assignment`), through the same
    compare-and-set as a manual assignment, so a person who takes the
    conversation at the same moment wins without a conflict.

    The assignment is audited without an actor and announced
    (`conversation.assigned`); `assigned_by` stays empty, which the cabinet
    shows as "assigned automatically". Sandbox work is never assigned.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        conversation_repo: ConversationTeamRepoContract,
        inbox_settings_repo: InboxSettingsRepoContract,
        audit_log_repo: AuditLogRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._inbox_settings_repo: InboxSettingsRepoContract = inbox_settings_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AutoAssignCommand) -> AutoAssignResult:
        if input_data.is_sandbox:
            return AutoAssignResult()

        settings: InboxSettingsDocument | None = (
            self._inbox_settings_repo.get_by_business(input_data.business_id)
        )
        if settings is None or not is_enabled_for(settings, input_data.trigger):
            return AutoAssignResult()

        conversation: ConversationDocument | None = self._conversation_repo.get(
            input_data.business_id, input_data.conversation_id
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if (
            conversation is None
            or business is None
            or conversation.is_sandbox
            or conversation.assignee_user_id is not None
        ):
            return AutoAssignResult()

        chosen: UserId | None = pick_assignee(
            auto_assign_candidates(business.members, settings.auto_assign_user_ids),
            self._conversation_repo.count_awaiting_by_assignee(business.id),
            settings.last_auto_assigned_user_id,
        )
        if chosen is None:
            return AutoAssignResult()

        now: Microseconds = self._wall_clock.now_unix()
        changed: ConversationDocument | None = self._conversation_repo.assign(
            business.id,
            conversation.id,
            ConversationAssignmentChange(
                assignee_user_id=chosen,
                expected_revision=conversation.assignment_revision,
                at=now,
            ),
        )
        if changed is None:
            # Someone assigned it meanwhile: their choice stands.
            return AutoAssignResult()

        def remember_turn(stored: InboxSettingsDocument) -> None:
            stored.last_auto_assigned_user_id = chosen

        self._inbox_settings_repo.change(business.id, remember_turn, now)
        append_audit(
            self._audit_log_repo,
            business.id,
            None,
            AuditAction.UPDATE,
            ASSIGNMENT_ENTITY,
            str(changed.id),
            None,
            now,
        )
        self._live_events.publish(
            business.id, LiveEventKind.CONVERSATION_ASSIGNED, (changed.id, chosen)
        )
        return AutoAssignResult(assignment=build_assignment_view(changed))


def is_enabled_for(settings: InboxSettingsDocument, trigger: InboxView) -> bool:
    if trigger is InboxView.NEEDS_PERSON:
        return settings.auto_assign_new_handoffs

    if trigger is InboxView.REQUESTS:
        return settings.auto_assign_new_requests

    return False
