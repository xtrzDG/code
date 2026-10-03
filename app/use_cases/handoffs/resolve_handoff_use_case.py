from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.booking_repositories import HandoffRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.operations.handoffs import HandoffListItem, ResolveHandoffCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.handoffs.handoff_views import build_handoff_list_item


class ResolveHandoffUseCase(UseCaseContract[ResolveHandoffCommand, HandoffListItem]):
    """
    Staff closes a handoff (RESOLVED with the time). The conversation goes
    back to OPEN, so the assistant answers again, unless another handoff of
    the same conversation is still open. Resolving twice is harmless.
    """

    def __init__(
        self,
        handoff_repo: HandoffRepoContract,
        conversation_repo: ConversationRepoContract,
        contact_repo: ContactRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events

    def run(self, input_data: ResolveHandoffCommand) -> HandoffListItem:
        handoff: HandoffDocument | None = self._handoff_repo.get(
            input_data.business_id, input_data.handoff_id
        )
        if handoff is None:
            raise NotFoundError(f"Handoff {input_data.handoff_id} was not found.")

        if handoff.status is not HandoffStatus.RESOLVED:
            now: Microseconds = self._wall_clock.now_unix()
            handoff.status = HandoffStatus.RESOLVED
            handoff.resolved_at = now
            handoff.updated_at = now
            self._handoff_repo.save(handoff)
            self._reopen_conversation(handoff, now)
            self._live_events.publish(
                handoff.business_id,
                LiveEventKind.HANDOFF_RESOLVED,
                (handoff.id, handoff.conversation_id),
                is_sandbox=handoff.is_sandbox,
            )

        return build_handoff_list_item(
            handoff,
            self._contact_repo.get(handoff.business_id, handoff.contact_id),
        )

    def _reopen_conversation(self, handoff: HandoffDocument, now: Microseconds) -> None:
        has_other_open_handoff: bool = any(
            other.conversation_id == handoff.conversation_id
            and other.id != handoff.id
            and other.status is not HandoffStatus.RESOLVED
            for other in self._handoff_repo.list_by_business(handoff.business_id)
        )
        if has_other_open_handoff:
            return

        conversation: ConversationDocument | None = self._conversation_repo.get(
            handoff.business_id, handoff.conversation_id
        )
        if (
            conversation is None
            or conversation.status is not ConversationStatus.HANDOFF
        ):
            return

        conversation.status = ConversationStatus.OPEN
        conversation.updated_at = now
        self._conversation_repo.save(conversation)
