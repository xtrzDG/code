from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.deliveries import OutboundAttempt
from app.schemas.dto.notifications.notification_settings import (
    NotificationCheckQueued,
    NotificationCheckResult,
    StaffDeliveryView,
)


class SendNotificationCheckOrchestrator[CheckRequest](
    OrchestratorContract[CheckRequest, NotificationCheckResult]
):
    """
    "Send a test" to a staff contact or a device: the check is stored in
    the outbox and sent at once through the same steps as every
    notification (send one attempt, record it), so the answer says whether
    it was delivered, failed with the provider's reason, or waits for a
    retry the worker makes (a temporary failure).
    """

    def __init__(
        self,
        queue_check: UseCaseContract[CheckRequest, NotificationCheckQueued],
        send_outbound_message: UseCaseContract[
            OutboundMessageDocument, OutboundAttempt
        ],
        record_outbound_attempt: UseCaseContract[
            OutboundAttempt, OutboundMessageDocument | None
        ],
    ) -> None:
        self._queue_check: UseCaseContract[CheckRequest, NotificationCheckQueued] = (
            queue_check
        )
        self._send_outbound_message: UseCaseContract[
            OutboundMessageDocument, OutboundAttempt
        ] = send_outbound_message
        self._record_outbound_attempt: UseCaseContract[
            OutboundAttempt, OutboundMessageDocument | None
        ] = record_outbound_attempt

    def execute(self, input_data: CheckRequest) -> NotificationCheckResult:
        queued: NotificationCheckQueued = self._queue_check.run(input_data)
        message: OutboundMessageDocument = queued.message
        if message.status is OutboundMessageStatus.PENDING:
            attempt: OutboundAttempt = self._send_outbound_message.run(message)
            message = self._record_outbound_attempt.run(attempt) or message

        return NotificationCheckResult(
            delivery=StaffDeliveryView(
                status=message.status,
                last_error=message.last_error,
                attempted_at=message.updated_at,
                delivered_at=message.delivered_at,
            ),
            is_simulated=queued.is_simulated,
        )
