from typed_time_provider import Microseconds

from app.contracts.telephony import CallFallbackAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.calls import MissedCallReason, MissedCallSource
from app.schemas.dto.calls.call_fallback import (
    CallFallbackReply,
    CallFallbackReport,
    CallFallbackWebhookRequest,
)
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    PreconditionFailedError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.telephony.strings import TwimlDocument
from app.utilities.calls.twilio_voice_webhooks import (
    build_dial_twiml,
    build_fallback_dial_path,
    build_hangup_twiml,
    build_voice_fallback_path,
    first_values,
    is_valid_twilio_signature,
    read_form_pairs,
    read_unanswered_reason,
)
from app.utilities.channels.channel_endpoints import join_public_url


class TwilioCallFallbackAdapter(CallFallbackAdapterContract):
    """
    Twilio's VoiceFallbackUrl of a rented number and the action of its
    <Dial>, signed with TWILIO_AUTH_TOKEN over the business's addresses
    under APP_BASE_URL (the ones its numbers were set up with), so a
    request names its business unforgeably. Without both settings no
    request is accepted: no number of this server sends one.

    The fallback names the call (`CallSid`), the line (`To`), the caller
    (`From`) and, for a call forwarded to the line, `ForwardedFrom`; the
    dial's action adds `DialCallStatus`. A missed call of the fallback is
    the line's (source PBX) of the business, keyed by Twilio's call SID.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._app_settings: AppSettings = app_settings

    def read_fallback(
        self,
        request: CallFallbackWebhookRequest,
        now: Microseconds,
    ) -> CallFallbackReport:
        fields: dict[str, str] = self._verified(
            request, build_voice_fallback_path(request.business_id)
        )
        return CallFallbackReport(
            provider_call_id=read_call_sid(fields),
            called_at=now,
            assistant_number=read_number(fields, "To"),
            caller_number=read_number(fields, "From"),
            forwarded_from=read_number(fields, "ForwardedFrom"),
        )

    def read_dial_outcome(
        self,
        request: CallFallbackWebhookRequest,
        now: Microseconds,
    ) -> MissedCallReport | None:
        fields: dict[str, str] = self._verified(
            request, build_fallback_dial_path(request.business_id)
        )
        call_id: ProviderCallId = read_call_sid(fields)
        reason: MissedCallReason | None = read_unanswered_reason(
            fields.get("DialCallStatus", "")
        )
        if reason is None:
            return None

        return MissedCallReport(
            source=MissedCallSource.PBX,
            provider_call_id=call_id,
            reason=reason,
            called_at=now,
            business_id=request.business_id,
            assistant_number=read_number(fields, "To"),
            caller_number=read_number(fields, "From"),
        )

    def transfer(
        self, business_id: BusinessId, phone_number: E164PhoneNumber
    ) -> CallFallbackReply:
        action_url: str | None = self._address(build_fallback_dial_path(business_id))
        if action_url is None:
            raise PreconditionFailedError("APP_BASE_URL is not set.")

        return CallFallbackReply(
            twiml=TwimlDocument(build_dial_twiml(str(phone_number), action_url))
        )

    def end_call(self) -> CallFallbackReply:
        return CallFallbackReply(twiml=TwimlDocument(build_hangup_twiml()))

    def _address(self, path: str) -> str | None:
        base_url = self._app_settings.app_base_url
        return None if base_url is None else join_public_url(str(base_url), path)

    def _verified(
        self, request: CallFallbackWebhookRequest, path: str
    ) -> dict[str, str]:
        """The form fields of a request Twilio signed for this address."""

        auth_token = self._app_settings.twilio_auth_token
        url: str | None = self._address(path)
        pairs: list[tuple[str, str]] = read_form_pairs(request.body)
        if (
            auth_token is None
            or url is None
            or not is_valid_twilio_signature(
                str(auth_token),
                url,
                pairs,
                None
                if request.signature_header is None
                else str(request.signature_header),
            )
        ):
            raise AuthenticationRequiredError(
                "The Twilio signature is missing or wrong."
            )

        return first_values(pairs)


def read_call_sid(fields: dict[str, str]) -> ProviderCallId:
    call_sid: str = fields.get("CallSid", "").strip()
    if not call_sid:
        raise ValidationFailedError("The Twilio request names no call.")

    return ProviderCallId(call_sid)


def read_number(fields: dict[str, str], name: str) -> RawPhoneNumberInput | None:
    value: str = fields.get(name, "").strip()
    return RawPhoneNumberInput(value) if value else None
