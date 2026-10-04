from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.booking_repositories import HandoffRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.operations.handoffs import HandoffListItem, ReopenHandoffCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.shared.handoff_views import HANDOFF_ENTITY, build_handoff_list_item
from app.use_cases.shared.operations_support import build_audit_entry

# A handoff resolved before resolving kept its status waits as notified.
UNKNOWN_STATUS_BEFORE_RESOLVE: HandoffStatus = HandoffStatus.NOTIFIED


class ReopenHandoffUseCase(UseCaseContract[ReopenHandoffCommand, HandoffListItem]):
    """
    Staff open a resolved handoff again (the Undo of "Resolved", or a
    problem that turned out not to be solved). The handoff gets back the
    status it had before it was resolved (notified when that is unknown)
    and waits for a person again; its conversation, which resolving gave
    back to the assistant, goes to HANDOFF again, so the assistant stays
    silent until staff resolve it (a closed conversation stays closed).

    Reopening an open handoff is harmless. The change is audited with the
    staff member and the cabinets of the business hear of it, without the
    new-handoff alert: the handoff is not new.
    """

    def __init__(
        self,
        handoff_repo: HandoffRepoContract,
        conversation_repo: ConversationRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ReopenHandoffCommand) -> HandoffListItem:
        handoff: HandoffDocument | None = self._handoff_repo.get(
            input_data.business_id, input_data.handoff_id
        )
        if handoff is None:
            raise NotFoundError(f"Handoff {input_data.handoff_id} was not found.")

        if handoff.status is HandoffStatus.RESOLVED:
            now: Microseconds = self._wall_clock.now_unix()
            handoff.status = handoff.status_before_resolve or (
                UNKNOWN_STATUS_BEFORE_RESOLVE
            )
            handoff.status_before_resolve = None
            handoff.resolved_at = None
            handoff.resolved_by = None
            handoff.updated_at = now
            self._handoff_repo.save(handoff)
            self._hand_conversation_back(handoff, now)
            self._audit_log_repo.append(
                build_audit_entry(
                    handoff.business_id,
                    input_data.actor_id,
                    AuditAction.UPDATE,
                    HANDOFF_ENTITY,
                    str(handoff.id),
                    now,
                )
            )
            self._live_events.publish(
                handoff.business_id,
                LiveEventKind.HANDOFF_REOPENED,
                (handoff.id, handoff.conversation_id),
                is_sandbox=handoff.is_sandbox,
            )

        return build_handoff_list_item(
            handoff,
            self._contact_repo.get(handoff.business_id, handoff.contact_id),
        )

    def _hand_conversation_back(
        self, handoff: HandoffDocument, now: Microseconds
    ) -> None:
        conversation: ConversationDocument | None = self._conversation_repo.get(
            handoff.business_id, handoff.conversation_id
        )
        if conversation is None or conversation.status is not ConversationStatus.OPEN:
            return

        conversation.status = ConversationStatus.HANDOFF
        conversation.updated_at = now
        self._conversation_repo.save(conversation)
