from typed_time_provider import Microseconds, WallClock

from app.adapters.voice.zadarma_replay_guard import ZadarmaReplayGuard
from app.contracts.rate_limits import RateLimitBucketAdapterContract
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
    is_recent_call_start,
    is_valid_zadarma_signature,
    read_call_start_seconds,
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

    The signature has no timestamp and leaves the call id out, so a
    notification whose signed `call_start` is not recent is refused like a
    wrong signature, and a copy of a signed notification under another call
    id is acknowledged and ignored (`ZadarmaReplayGuard`).
    """

    def __init__(
        self,
        app_settings: AppSettings,
        buckets: RateLimitBucketAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._app_settings: AppSettings = app_settings
        self._replay_guard: ZadarmaReplayGuard = ZadarmaReplayGuard(buckets)
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def verify_signature(self, request: PbxCallWebhookRequest) -> None:
        api_secret: PlatformSecret | None = self._app_settings.zadarma_api_secret
        fields: dict[str, str] = read_form_fields(request.body)
        if api_secret is None or not is_valid_zadarma_signature(
            str(api_secret),
            fields,
            None if request.signature_header is None else str(request.signature_header),
        ):
            raise AuthenticationRequiredError(
                "The Zadarma signature is missing or wrong."
            )

        call_start: int | None = read_call_start_seconds(fields)
        now_seconds: int = int(self._wall_clock.now_unix()) // MICROSECONDS_PER_SECOND
        if call_start is None or not is_recent_call_start(call_start, now_seconds):
            raise AuthenticationRequiredError(
                "The Zadarma notification is not recent (call_start)."
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

        call_start: int | None = read_call_start_seconds(fields)
        if call_start is not None and self._replay_guard.is_replay(fields, call_start):
            return None

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
