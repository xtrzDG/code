from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.channels.inbox.inbound_event_orchestrator import (
    InboundEventOrchestrator,
)
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.staff_links import (
    PlatformBotUpdate,
    PlatformBotWebhookOutcome,
)
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboundFailure
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.exceptions.application_errors import ValidationFailedError


class ProcessPlatformBotUpdateOrchestrator(InboundEventOrchestrator):
    """
    `process_platform_bot_update`: a staff message to the platform bot that
    the webhook stored ("/start <code>" links the chat, anything else gets
    the instructions), handled in the worker.
    """

    def __init__(
        self,
        claim_inbound_event: UseCaseContract[QueuedJobInput, InboundEventClaim | None],
        handle_platform_bot_update: UseCaseContract[
            PlatformBotUpdate, PlatformBotWebhookOutcome
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
        self._handle_platform_bot_update: UseCaseContract[
            PlatformBotUpdate, PlatformBotWebhookOutcome
        ] = handle_platform_bot_update

    def _process(self, claim: InboundEventClaim) -> InboundAnswer:
        if claim.event.payload is None:
            raise ValidationFailedError("The inbox event holds no bot update.")

        self._handle_platform_bot_update.run(
            PlatformBotUpdate(body=str(claim.event.payload).encode("utf-8"))
        )
        return InboundAnswer(event=claim.event)
