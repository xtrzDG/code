import logging

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboundFailure
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.utilities.deliveries.inbound_failures import (
    describe_inbound_error,
    is_final_inbound_failure,
    is_inbound_refusal,
)

logger: logging.Logger = logging.getLogger(__name__)


class InboundEventOrchestrator(OrchestratorContract[QueuedJobInput, JobReport]):
    """
    The worker's side of the inbox: one job processes one event. Take the
    event (held until its lease ends), process it (`_process`, per kind of
    event), then close it.

    A refusal (the business is not live, an invalid payload) marks the
    event FAILED and ends the job. A temporary failure gives the event up
    and fails the job, which runs again with backoff; on the job's last
    attempt the event is FAILED too. A worker that dies mid-turn leaves the
    event held: once the leases run out, the job and the event are taken
    over and the turn runs again (the reply it stored is reused).
    """

    def __init__(
        self,
        claim_inbound_event: UseCaseContract[QueuedJobInput, InboundEventClaim | None],
        finish_inbound_event: UseCaseContract[
            InboundAnswer, InboundEventDocument | None
        ],
        release_inbound_event: UseCaseContract[
            InboundFailure, InboundEventDocument | None
        ],
    ) -> None:
        self._claim_inbound_event: UseCaseContract[
            QueuedJobInput, InboundEventClaim | None
        ] = claim_inbound_event
        self._finish_inbound_event: UseCaseContract[
            InboundAnswer, InboundEventDocument | None
        ] = finish_inbound_event
        self._release_inbound_event: UseCaseContract[
            InboundFailure, InboundEventDocument | None
        ] = release_inbound_event

    def execute(self, input_data: QueuedJobInput) -> JobReport:
        claim: InboundEventClaim | None = self._claim_inbound_event.run(input_data)
        if claim is None:
            return JobReport()

        try:
            answer: InboundAnswer = self._process(claim)
            self._finish_inbound_event.run(answer)
        except Exception as error:
            is_final: bool = is_final_inbound_failure(
                error, input_data.is_final_attempt
            )
            self._release_inbound_event.run(
                InboundFailure(
                    event_id=claim.event.id,
                    business_id=claim.event.business_id,
                    error=describe_inbound_error(error),
                    is_final=is_final,
                )
            )
            if not is_inbound_refusal(error):
                raise

            logger.warning(
                "A %s event of business %s was not processed: %s",
                claim.event.channel.value,
                claim.event.business_id,
                error,
            )
            return JobReport()

        return JobReport(processed_count=ProcessedItemCount(1))

    def _process(self, claim: InboundEventClaim) -> InboundAnswer:
        raise NotImplementedError
