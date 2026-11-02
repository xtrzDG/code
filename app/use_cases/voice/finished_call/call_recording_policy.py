"""
Whether the platform keeps a finished call's audio: only when the owner
turned the recording on in Settings → Calls (off by default), never for a
call a person took after a transfer, whose audio holds the staff
member's conversation (the report is read without it,
`items_before_staff`), and never for a call whose caller read out a card
number or a security code (the transcript has them masked; the audio
would keep them, and the platform keeps no card data, PCI DSS SAQ A).
"""

from app.schemas.constants.calls import CallTransferOutcome
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport
from app.utilities.privacy.sensitive_numbers import holds_masked_card_data


def keeps_call_recording(
    report: FinishedCallReport,
    call_settings: CallSettingsDocument | None,
) -> bool:
    """
    The call's audio is kept: recording on, no person took a transfer and
    no card data was said.
    """

    if call_settings is None or not call_settings.is_recording_enabled:
        return False

    if any(holds_masked_card_data(str(line.text)) for line in report.transcript):
        return False

    return report.transfer_outcome is not CallTransferOutcome.CONNECTED
