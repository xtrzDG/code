from typed_time_provider import Microseconds

from app.contracts.telephony import PbxWebhookAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.calls import MissedCallReason, MissedCallSource
from app.schemas.dto.calls.missed_calls import MissedCallReport, PbxCallWebhookRequest
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.calls.zadarma_notifications import (
    NOTIFY_END_EVENT,
    is_valid_zadarma_signature,
    read_form_fields,
    read_missed_reason,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
MAX_RING_SECONDS: int = 24 * 60 * 60


class ZadarmaPbxWebhookAdapter(PbxWebhookAdapterContract):
    """
    Call notifications of the Zadarma PBX (ZADARMA_API_SECRET signs them).

    NOTIFY_END reports how an incoming call to the PBX ended: `pbx_call_id`,
    `caller_id`, `called_did` (the assistant's number), `duration` and
    `disposition`. A call the line did not put through ("busy",
    "no answer", "cancel", a failed line) is a missed call that started
    `duration` seconds before the notification; an answered one is the
    voice platform's to report.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._app_settings: AppSettings = app_settings

    def verify_signature(self, request: PbxCallWebhookRequest) -> None:
        api_secret: PlatformSecret | None = self._app_settings.zadarma_api_secret
        if api_secret is None or not is_valid_zadarma_signature(
            str(api_secret),
            read_form_fields(request.body),
            None if request.signature_header is None else str(request.signature_header),
        ):
            raise AuthenticationRequiredError(
                "The Zadarma signature is missing or wrong."
            )

    def parse_missed_call(
        self,
        request: PbxCallWebhookRequest,
        now: Microseconds,
    ) -> MissedCallReport | None:
        fields: dict[str, str] = read_form_fields(request.body)
        if fields.get("event") != NOTIFY_END_EVENT:
            return None

        reason: MissedCallReason | None = read_missed_reason(
            fields.get("disposition", "")
        )
        if reason is None:
            return None

        call_id: str = fields.get("pbx_call_id", "").strip()
        if not call_id:
            raise ValidationFailedError("The PBX notification names no call.")

        caller: str = fields.get("caller_id", "").strip()
        called: str = fields.get("called_did", "").strip()
        return MissedCallReport(
            source=MissedCallSource.PBX,
            provider_call_id=ProviderCallId(call_id),
            reason=reason,
            called_at=Microseconds(
                int(now)
                - read_seconds(fields.get("duration")) * MICROSECONDS_PER_SECOND
            ),
            assistant_number=RawPhoneNumberInput(called) if called else None,
            caller_number=RawPhoneNumberInput(caller) if caller else None,
        )


def read_seconds(raw: str | None) -> int:
    """A ring time in whole seconds (0 when missing or unreadable)."""

    try:
        seconds: int = int(raw or "0")
    except ValueError:
        return 0

    return min(max(seconds, 0), MAX_RING_SECONDS)
