from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.channels.inbox.inbound_event_orchestrator import (
    InboundEventOrchestrator,
)
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboundFailure
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.voice_webhooks import (
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
)
from app.schemas.exceptions.application_errors import ValidationFailedError


class ProcessPostCallOrchestrator(InboundEventOrchestrator):
    """
    `process_post_call`: a finished-call report the webhook verified and
    stored, processed in the worker by the post-call flow (store the call
    with its outcome and cost, confirm a booking to the caller). The flow
    reads the stored report without checking the signature again: it was
    checked when the report arrived, and a retry may come after the
    signature's 30 minutes.
    """

    def __init__(
        self,
        claim_inbound_event: UseCaseContract[QueuedJobInput, InboundEventClaim | None],
        process_finished_call: OrchestratorContract[
            PostCallWebhookRequest, PostCallWebhookOutcome
        ],
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
        self._process_finished_call: OrchestratorContract[
            PostCallWebhookRequest, PostCallWebhookOutcome
        ] = process_finished_call

    def _process(self, claim: InboundEventClaim) -> InboundAnswer:
        if claim.event.payload is None:
            raise ValidationFailedError("The inbox event holds no call report.")

        self._process_finished_call.execute(
            PostCallWebhookRequest(body=str(claim.event.payload).encode("utf-8"))
        )
        return InboundAnswer(event=claim.event)
