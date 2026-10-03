from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.channels.post_call_follow_ups import PostCallFollowUps
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.call_audits import CallAuditRequest
from app.schemas.dto.calls.call_summaries import CallSummaryRequest
from app.schemas.dto.calls.missed_calls import (
    MissedCallReport,
    RegisteredMissedCall,
    StoredFinishedCall,
)
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
    RecordedCall,
)
from app.schemas.typings.channels.booleans import (
    IsCallConfirmationSent,
)


class PostCallWebhookOrchestrator(
    OrchestratorContract[PostCallWebhookRequest, PostCallWebhookOutcome]
):
    """
    Post-call webhook of the voice platform (concept section 7): verify it,
    store the call with its outcome and cost (a call the caller spoke in
    gets a conversation, so its card shows it), check what the assistant
    said against the business data (the invented-numbers guard, with a
    handoff when a booking or lead was made on unverified values), text a
    caller who did not get what they called for (hung up without a word,
    or nobody picked up the transfer), send staff the call's summary,
    confirm a booking made during the call by a messenger message, text
    the links the assistant promised, and queue the archive of the
    recording into the EU object storage.
    """

    def __init__(
        self,
        authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest,
            FinishedCallReport | None,
        ],
        record_finished_call: UseCaseContract[FinishedCallReport, RecordedCall],
        follow_ups: PostCallFollowUps,
    ) -> None:
        self._authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest,
            FinishedCallReport | None,
        ] = authenticate_post_call
        self._record_finished_call: UseCaseContract[
            FinishedCallReport, RecordedCall
        ] = record_finished_call
        self._steps: PostCallFollowUps = follow_ups

    def execute(self, input_data: PostCallWebhookRequest) -> PostCallWebhookOutcome:
        report: FinishedCallReport | None = self._authenticate_post_call.run(input_data)
        if report is None:
            return PostCallWebhookOutcome(status=PostCallEventStatus.IGNORED)

        recorded: RecordedCall = self._steps.open_call_conversation.run(
            StoredFinishedCall(
                report=report, call=self._record_finished_call.run(report)
            )
        )
        self._steps.audit_call_replies.run(
            CallAuditRequest(call=recorded, transcript=report.transcript)
        )
        missed_call: MissedCallDocument | None = self._register_missed_caller(
            StoredFinishedCall(report=report, call=recorded)
        )
        self._steps.summarize_call.run(
            CallSummaryRequest(
                call=recorded, transcript=report.transcript, missed_call=missed_call
            )
        )
        is_confirmation_sent: IsCallConfirmationSent = (
            self._steps.send_call_confirmation.run(recorded)
        )
        self._steps.send_call_links.run(recorded)
        self._steps.schedule_recording_archive.run(recorded)
        return PostCallWebhookOutcome(
            status=recorded.status,
            call_id=recorded.call_id,
            outcome=recorded.outcome,
            is_confirmation_sent=is_confirmation_sent,
        )

    def _register_missed_caller(
        self, stored: StoredFinishedCall
    ) -> MissedCallDocument | None:
        missed: MissedCallReport | None = self._steps.find_missed_voice_call.run(stored)
        registered: RegisteredMissedCall | None = (
            None if missed is None else self._steps.register_missed_call.run(missed)
        )
        return None if registered is None else registered.missed_call
