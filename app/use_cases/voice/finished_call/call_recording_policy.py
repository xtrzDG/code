"""
Whether the platform keeps a finished call's audio: only when the owner
turned the recording on in Settings → Calls (off by default), and never
for a call a person took after a transfer, whose audio holds the staff
member's conversation (the report is read without it,
`items_before_staff`).
"""

from app.schemas.constants.calls import CallTransferOutcome
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport


def keeps_call_recording(
    report: FinishedCallReport,
    call_settings: CallSettingsDocument | None,
) -> bool:
    """The call's audio is kept: recording on, and no person took a transfer."""

    if call_settings is None or not call_settings.is_recording_enabled:
        return False

    return report.transfer_outcome is not CallTransferOutcome.CONNECTED
