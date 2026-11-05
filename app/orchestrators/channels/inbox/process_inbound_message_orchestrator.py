import logging

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.channels.inbox.customer_wait import CustomerWait
from app.orchestrators.channels.inbox.inbound_burst_answers import (
    InboundBurstAnswers,
)
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundAnswer, InboundFailure
from app.schemas.dto.inbound_bursts import HeldInboundEvents, InboundBurst
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.utilities.deliveries.inbound_failures import (
    describe_inbound_error,
    is_final_inbound_failure,
    is_inbound_refusal,
)

logger: logging.Logger = logging.getLogger(__name__)


class ProcessInboundMessageOrchestrator(
    OrchestratorContract[QueuedJobInput, JobReport]
):
    """
    `process_inbound_message`: answer a customer's messages from the inbox
    in the worker (concept section 1, path of a message), fast:

    - The customer sees "typing…" at once, and again until the reply is
      written (Telegram, WhatsApp, Messenger, Instagram).
    - Quick messages in a row get one reply: the job waits for the customer
      to be quiet for MESSAGE_COALESCE_SECONDS by queuing itself again
      (`claim_inbound_burst`), then answers all of them in one turn.
    - A turn still running CHAT_TURN_DEADLINE_SECONDS after the first of
      them sends a short "one moment" once (`TurnDeadlineWatch`).

    The answer goes into the outbox; every message of the burst is closed
    with it. A refusal (the business is not live, an invalid payload) marks
    the messages FAILED and ends the job; a temporary failure gives them up
    and fails the job, which runs again with backoff (on its last attempt
    its own message is FAILED). A reply an earlier attempt already stored
    is sent instead of asking the model again.
    """

    def __init__(
        self,
        claim_inbound_burst: UseCaseContract[QueuedJobInput, InboundBurst | None],
        answers: InboundBurstAnswers,
        finish_inbound_event: UseCaseContract[
            InboundAnswer, InboundEventDocument | None
        ],
        finish_held_inbound_events: UseCaseContract[
            HeldInboundEvents, ProcessedItemCount
        ],
        release_inbound_event: UseCaseContract[
            InboundFailure, InboundEventDocument | None
        ],
        customer_wait: CustomerWait,
    ) -> None:
        self._claim_inbound_burst: UseCaseContract[
            QueuedJobInput, InboundBurst | None
        ] = claim_inbound_burst
        self._answers: InboundBurstAnswers = answers
        self._finish_inbound_event: UseCaseContract[
            InboundAnswer, InboundEventDocument | None
        ] = finish_inbound_event
        self._finish_held_inbound_events: UseCaseContract[
            HeldInboundEvents, ProcessedItemCount
        ] = finish_held_inbound_events
        self._release_inbound_event: UseCaseContract[
            InboundFailure, InboundEventDocument | None
        ] = release_inbound_event
        self._customer_wait: CustomerWait = customer_wait

    def execute(self, input_data: QueuedJobInput) -> JobReport:
        burst: InboundBurst | None = self._claim_inbound_burst.run(input_data)
        if burst is None:
            return JobReport()

        if not burst.claims:
            # The customer may still be writing: typing now, the answer when
            # they are quiet (the job comes back then).
            self._customer_wait.acknowledge(burst.trigger)
            return JobReport()

        try:
            with self._customer_wait.while_answering(
                burst.claims[-1].event, burst.claims[0].event.created_at
            ):
                answers: list[InboundAnswer] = self._answers.answer(burst)

            self._finish(answers)
        except Exception as error:
            if not self._release(burst, error):
                raise

            logger.warning(
                "A %s event of business %s was not processed: %s",
                burst.trigger.channel.value,
                burst.trigger.business_id,
                error,
            )
            return JobReport()

        return JobReport(processed_count=ProcessedItemCount(len(burst.claims)))

    def _finish(self, answers: list[InboundAnswer]) -> None:
        """
        Replies in order (a platform's own answer to an earlier message, e.g.
        STOP, before the burst's answer), then the messages the answer
        covers take its outcome.
        """

        final: InboundAnswer = answers[-1]
        held: list[InboundEventDocument] = []
        for answer in answers[:-1]:
            if answer.text is None:
                held.append(answer.event)
            else:
                self._finish_inbound_event.run(answer)

        finished: InboundEventDocument | None = self._finish_inbound_event.run(final)
        if held and finished is not None:
            self._finish_held_inbound_events.run(
                HeldInboundEvents(events=held, answered_by=finished)
            )

    def _release(self, burst: InboundBurst, error: Exception) -> bool:
        """Give the messages up; True when the failure was a refusal."""

        for claim in burst.claims:
            self._release_inbound_event.run(
                InboundFailure(
                    event_id=claim.event.id,
                    business_id=claim.event.business_id,
                    error=describe_inbound_error(error),
                    is_final=is_final_inbound_failure(error, claim.is_final_attempt),
                )
            )

        return is_inbound_refusal(error)
