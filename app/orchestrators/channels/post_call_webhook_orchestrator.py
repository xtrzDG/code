from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.dto.call_audits import CallAudit, CallAuditRequest
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
    RecordedCall,
)
from app.schemas.typings.channels.booleans import (
    IsCallConfirmationSent,
    IsCallLinkMessageSent,
)


class PostCallWebhookOrchestrator(
    OrchestratorContract[PostCallWebhookRequest, PostCallWebhookOutcome]
):
    """
    Post-call webhook of the voice platform (concept section 7): verify it,
    store the call with its outcome and cost, check what the assistant said
    against the business data (the invented-numbers guard, with a handoff
    when a booking or lead was made on unverified values), confirm a
    booking made during the call by a messenger message, and text the links
    the assistant promised.
    """

    def __init__(
        self,
        authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest,
            FinishedCallReport | None,
        ],
        record_finished_call: UseCaseContract[FinishedCallReport, RecordedCall],
        audit_call_replies: UseCaseContract[CallAuditRequest, CallAudit],
        send_call_confirmation: UseCaseContract[RecordedCall, IsCallConfirmationSent],
        send_call_links: UseCaseContract[RecordedCall, IsCallLinkMessageSent],
    ) -> None:
        self._authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest,
            FinishedCallReport | None,
        ] = authenticate_post_call
        self._record_finished_call: UseCaseContract[
            FinishedCallReport, RecordedCall
        ] = record_finished_call
        self._audit_call_replies: UseCaseContract[CallAuditRequest, CallAudit] = (
            audit_call_replies
        )
        self._send_call_confirmation: UseCaseContract[
            RecordedCall,
            IsCallConfirmationSent,
        ] = send_call_confirmation
        self._send_call_links: UseCaseContract[RecordedCall, IsCallLinkMessageSent] = (
            send_call_links
        )

    def execute(self, input_data: PostCallWebhookRequest) -> PostCallWebhookOutcome:
        report: FinishedCallReport | None = self._authenticate_post_call.run(input_data)
        if report is None:
            return PostCallWebhookOutcome(status=PostCallEventStatus.IGNORED)

        recorded_call: RecordedCall = self._record_finished_call.run(report)
        self._audit_call_replies.run(
            CallAuditRequest(call=recorded_call, transcript=report.transcript)
        )
        is_confirmation_sent: IsCallConfirmationSent = self._send_call_confirmation.run(
            recorded_call
        )
        self._send_call_links.run(recorded_call)
        return PostCallWebhookOutcome(
            status=recorded_call.status,
            call_id=recorded_call.call_id,
            outcome=recorded_call.outcome,
            is_confirmation_sent=is_confirmation_sent,
        )
