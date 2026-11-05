import logging

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.deliveries import OutboundAttempt
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount

logger: logging.Logger = logging.getLogger(__name__)


class DeliverOutboundMessageOrchestrator(
    OrchestratorContract[QueuedJobInput, JobReport]
):
    """
    `deliver_outbound`: send one outbox message when it is due, store the
    outcome (delivered, retry later, or given up) and, for a reply the
    customer will never get, hand the conversation to staff.
    """

    def __init__(
        self,
        take_due_outbound_message: UseCaseContract[
            QueuedJobInput, OutboundMessageDocument | None
        ],
        send_outbound_message: UseCaseContract[
            OutboundMessageDocument, OutboundAttempt
        ],
        record_outbound_attempt: UseCaseContract[
            OutboundAttempt, OutboundMessageDocument | None
        ],
        build_undelivered_reply_handoff: UseCaseContract[
            OutboundMessageDocument, HandoffCommand | None
        ],
        handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
    ) -> None:
        self._take_due_outbound_message: UseCaseContract[
            QueuedJobInput, OutboundMessageDocument | None
        ] = take_due_outbound_message
        self._send_outbound_message: UseCaseContract[
            OutboundMessageDocument, OutboundAttempt
        ] = send_outbound_message
        self._record_outbound_attempt: UseCaseContract[
            OutboundAttempt, OutboundMessageDocument | None
        ] = record_outbound_attempt
        self._build_undelivered_reply_handoff: UseCaseContract[
            OutboundMessageDocument, HandoffCommand | None
        ] = build_undelivered_reply_handoff
        self._handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult] = (
            handoff_to_human
        )

    def execute(self, input_data: QueuedJobInput) -> JobReport:
        message: OutboundMessageDocument | None = self._take_due_outbound_message.run(
            input_data
        )
        if message is None:
            return JobReport()

        attempt: OutboundAttempt = self._send_outbound_message.run(message)
        stored: OutboundMessageDocument | None = self._record_outbound_attempt.run(
            attempt
        )
        if stored is not None:
            self._hand_off_if_undelivered(stored)

        return JobReport(processed_count=ProcessedItemCount(1))

    def _hand_off_if_undelivered(self, message: OutboundMessageDocument) -> None:
        command: HandoffCommand | None = self._build_undelivered_reply_handoff.run(
            message
        )
        if command is None:
            return

        try:
            self._handoff_to_human.run(command)
        except ApplicationError:
            logger.exception(
                "The undelivered reply %s could not be handed to staff.", message.id
            )
