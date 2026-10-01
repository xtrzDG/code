from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
    RecordedCall,
)
from app.schemas.typings.channels.booleans import IsCallConfirmationSent


class PostCallWebhookOrchestrator(
    OrchestratorContract[PostCallWebhookRequest, PostCallWebhookOutcome]
):
    """
    Post-call webhook of the voice platform (concept section 7): verify it,
    store the call with its outcome and cost, and confirm a booking made
    during the call by a messenger message.
    """

    def __init__(
        self,
        authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest,
            FinishedCallReport | None,
        ],
        record_finished_call: UseCaseContract[FinishedCallReport, RecordedCall],
        send_call_confirmation: UseCaseContract[RecordedCall, IsCallConfirmationSent],
    ) -> None:
        self._authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest,
            FinishedCallReport | None,
        ] = authenticate_post_call
        self._record_finished_call: UseCaseContract[
            FinishedCallReport, RecordedCall
        ] = record_finished_call
        self._send_call_confirmation: UseCaseContract[
            RecordedCall,
            IsCallConfirmationSent,
        ] = send_call_confirmation

    def execute(self, input_data: PostCallWebhookRequest) -> PostCallWebhookOutcome:
        report: FinishedCallReport | None = self._authenticate_post_call.run(input_data)
        if report is None:
            return PostCallWebhookOutcome(status=PostCallEventStatus.IGNORED)

        recorded_call: RecordedCall = self._record_finished_call.run(report)
        is_confirmation_sent: IsCallConfirmationSent = self._send_call_confirmation.run(
            recorded_call
        )
        return PostCallWebhookOutcome(
            status=recorded_call.status,
            call_id=recorded_call.call_id,
            outcome=recorded_call.outcome,
            is_confirmation_sent=is_confirmation_sent,
        )
