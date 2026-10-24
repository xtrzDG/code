"""The steps of the post-call flow after the call is stored."""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.call_audits import CallAudit, CallAuditRequest
from app.schemas.dto.calls.call_summaries import CallSummaryOutcome, CallSummaryRequest
from app.schemas.dto.calls.missed_calls import (
    MissedCallReport,
    RegisteredMissedCall,
    StoredFinishedCall,
)
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.channels.booleans import (
    IsCallConfirmationSent,
    IsCallLinkMessageSent,
)
from app.schemas.typings.conversations.booleans import IsRecordingArchiveScheduled


class PostCallFollowUps:
    """
    The use cases that follow a stored call, in the order the post-call
    flow runs them (one constructor argument instead of eight).
    """

    def __init__(
        self,
        open_call_conversation: UseCaseContract[StoredFinishedCall, RecordedCall],
        audit_call_replies: UseCaseContract[CallAuditRequest, CallAudit],
        find_missed_voice_call: UseCaseContract[
            StoredFinishedCall, MissedCallReport | None
        ],
        register_missed_call: UseCaseContract[
            MissedCallReport, RegisteredMissedCall | None
        ],
        summarize_call: UseCaseContract[CallSummaryRequest, CallSummaryOutcome],
        send_call_confirmation: UseCaseContract[RecordedCall, IsCallConfirmationSent],
        send_call_links: UseCaseContract[RecordedCall, IsCallLinkMessageSent],
        schedule_recording_archive: UseCaseContract[
            RecordedCall, IsRecordingArchiveScheduled
        ],
    ) -> None:
        self.open_call_conversation: UseCaseContract[
            StoredFinishedCall, RecordedCall
        ] = open_call_conversation
        self.audit_call_replies: UseCaseContract[CallAuditRequest, CallAudit] = (
            audit_call_replies
        )
        self.find_missed_voice_call: UseCaseContract[
            StoredFinishedCall, MissedCallReport | None
        ] = find_missed_voice_call
        self.register_missed_call: UseCaseContract[
            MissedCallReport, RegisteredMissedCall | None
        ] = register_missed_call
        self.summarize_call: UseCaseContract[CallSummaryRequest, CallSummaryOutcome] = (
            summarize_call
        )
        self.send_call_confirmation: UseCaseContract[
            RecordedCall, IsCallConfirmationSent
        ] = send_call_confirmation
        self.send_call_links: UseCaseContract[RecordedCall, IsCallLinkMessageSent] = (
            send_call_links
        )
        self.schedule_recording_archive: UseCaseContract[
            RecordedCall, IsRecordingArchiveScheduled
        ] = schedule_recording_archive
