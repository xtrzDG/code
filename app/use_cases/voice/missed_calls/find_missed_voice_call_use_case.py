from collections.abc import Sequence

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calls import (
    CallTransferOutcome,
    MissedCallReason,
    MissedCallSource,
)
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.conversations import CallOutcome, MessageAuthor
from app.schemas.dto.calls.missed_calls import MissedCallReport, StoredFinishedCall
from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.dto.voice_webhooks import FinishedCallReport, RecordedCall
from app.utilities.storage.release_gates import CALLBACK_REQUESTED_GATE, is_gate_open

# Calls that leave staff a booking, a request or a handoff to act on.
OUTCOMES_STAFF_ACT_ON: frozenset[CallOutcome] = frozenset(
    {CallOutcome.BOOKING, CallOutcome.LEAD, CallOutcome.HANDOFF}
)


class FindMissedVoiceCallUseCase(
    UseCaseContract[StoredFinishedCall, MissedCallReport | None]
):
    """
    A call the phone assistant answered whose caller still did not get
    what they called for: they hung up without saying a word (during the
    greeting), asked for a person and nobody picked up the transfer, or
    asked to be called back by a person (the voice platform's evaluation
    read it) in a call that left staff nothing to act on (no booking,
    request, handoff or transfer someone answered). None for every other
    call, and for a call that was not stored.
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
        elif is_callback_left_open(report, call):
            reason = callback_reason()

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


def is_callback_left_open(report: FinishedCallReport, call: RecordedCall) -> bool:
    """
    The caller asked for a person to call back, nobody got a task and no
    one took the call over (a transfer that connected is answered).
    """

    return (
        report.analysis is not None
        and report.analysis.callback_requested is True
        and call.outcome not in OUTCOMES_STAFF_ACT_ON
        and report.transfer_outcome is not CallTransferOutcome.CONNECTED
    )


def callback_reason(gates: Sequence[ReleaseGate] | None = None) -> MissedCallReason:
    """
    CALLBACK_REQUESTED once its release gate opens (the release before reads
    it then); TRANSFER_UNANSWERED until that release.
    """

    if is_gate_open(CALLBACK_REQUESTED_GATE, gates):
        return MissedCallReason.CALLBACK_REQUESTED

    return MissedCallReason.TRANSFER_UNANSWERED
