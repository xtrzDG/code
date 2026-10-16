from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calls import (
    CallTransferOutcome,
    MissedCallReason,
    MissedCallSource,
)
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.calls.missed_calls import MissedCallReport, StoredFinishedCall
from app.schemas.dto.voice_webhooks import FinishedCallReport, RecordedCall


class FindMissedVoiceCallUseCase(
    UseCaseContract[StoredFinishedCall, MissedCallReport | None]
):
    """
    A call the phone assistant answered whose caller still did not get
    what they called for: they hung up without saying a word (during the
    greeting), or asked for a person and nobody picked up the transfer.
    None for every other call, and for a call that was not stored.
    """

    def run(self, input_data: StoredFinishedCall) -> MissedCallReport | None:
        report: FinishedCallReport = input_data.report
        call: RecordedCall = input_data.call
        if call.status is PostCallEventStatus.IGNORED or call.business_id is None:
            return None

        reason: MissedCallReason | None = None
        if not any(line.author is MessageAuthor.CUSTOMER for line in report.transcript):
            reason = MissedCallReason.NO_SPEECH
        elif report.transfer_outcome is CallTransferOutcome.UNANSWERED:
            reason = MissedCallReason.TRANSFER_UNANSWERED

        if reason is None:
            return None

        return MissedCallReport(
            source=MissedCallSource.VOICE_PLATFORM,
            provider_call_id=report.provider_call_id,
            reason=reason,
            called_at=report.started_at,
            business_id=call.business_id,
            caller_number=report.caller_number,
            language=report.language,
            call_id=call.call_id,
        )
