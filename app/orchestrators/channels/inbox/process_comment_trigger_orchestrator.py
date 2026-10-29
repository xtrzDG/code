from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.channels.inbox.inbound_event_orchestrator import (
    InboundEventOrchestrator,
)
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboundFailure
from app.schemas.dto.jobs import QueuedJobInput


class ProcessCommentTriggerOrchestrator(InboundEventOrchestrator):
    """
    `process_comment_trigger`: an Instagram comment that named one of the
    owner's keywords, taken from the inbox by the worker; its private reply
    goes into the outbox (`ReplyToCommentTriggerUseCase`) and the event is
    closed. A reply over its limits leaves the event FAILED.
    """

    def __init__(
        self,
        claim_inbound_event: UseCaseContract[QueuedJobInput, InboundEventClaim | None],
        reply_to_comment: UseCaseContract[InboundEventClaim, InboundAnswer],
        finish_inbound_event: UseCaseContract[
            InboundAnswer, InboundEventDocument | None
        ],
        release_inbound_event: UseCaseContract[
            InboundFailure, InboundEventDocument | None
        ],
    ) -> None:
        super().__init__(
            claim_inbound_event, finish_inbound_event, release_inbound_event
        )
        self._reply_to_comment: UseCaseContract[InboundEventClaim, InboundAnswer] = (
            reply_to_comment
        )

    def _process(self, claim: InboundEventClaim) -> InboundAnswer:
        return self._reply_to_comment.run(claim)
