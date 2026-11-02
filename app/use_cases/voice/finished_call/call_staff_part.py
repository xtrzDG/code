"""
The part of a call after a person took the transfer is the staff
member's conversation, not the assistant's (Italian labour law protects
it: Statuto dei Lavoratori art. 4 on tools that can monitor staff).

The platform keeps none of it: a report of a call a person picked up is
read without the transcript lines from the transfer on and without the
voice platform's evaluation (made from the whole call), so no stored
transcript, summary, audit or memory carries the staff part; and its
audio, which holds that part too, is not kept (`keeps_call_recording`).
"""

from app.schemas.constants.calls import CallTransferOutcome
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport


def without_staff_part(report: FinishedCallReport) -> FinishedCallReport:
    """The report up to the transfer, when a person took it; else as it is."""

    if (
        report.transfer_outcome is not CallTransferOutcome.CONNECTED
        or report.transfer_offset_seconds is None
    ):
        return report

    transfer_offset: int = int(report.transfer_offset_seconds)
    return report.model_copy(
        update={
            "transcript": [
                line
                for line in report.transcript
                if int(line.offset_seconds) < transfer_offset
            ],
            "analysis": None,
        }
    )


def keeps_call_recording(
    report: FinishedCallReport,
    call_settings: CallSettingsDocument | None,
) -> bool:
    """
    The call's audio is kept only when the owner turned the recording on
    (off without settings) and no person took a transfer during the call.
    """

    if call_settings is None or not call_settings.is_recording_enabled:
        return False

    return report.transfer_outcome is not CallTransferOutcome.CONNECTED
