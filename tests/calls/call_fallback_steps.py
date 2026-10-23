"""
A business whose rented line falls back to the staff mobile, and the steps
of the call fallback tests: Twilio's signed fallback and dial requests
over the real router, the staff mobile in the profile, the owner's notices.
"""

import base64
import hashlib
import hmac
from urllib.parse import urlencode

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.telephony.twilio_call_fallback_adapter import (
    TwilioCallFallbackAdapter,
)
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.twilio_voice_routes import build_twilio_voice_router
from app.orchestrators.voice.call_fallback_orchestrator import (
    CallFallbackOrchestrator,
)
from app.orchestrators.voice.fallback_dial_orchestrator import (
    FallbackDialOrchestrator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.profiles import BusinessContacts, BusinessProfileDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.use_cases.voice.fallback.notify_call_fallback_use_case import (
    NotifyCallFallbackUseCase,
)
from app.use_cases.voice.fallback.read_fallback_dial_use_case import (
    ReadFallbackDialUseCase,
)
from app.use_cases.voice.fallback.route_call_fallback_use_case import (
    RouteCallFallbackUseCase,
)
from tests.channels.channels_http import wrap
from tests.channels.channels_payloads import HttpResponse
from tests.channels.channels_settings import APP_BASE_URL, build_settings
from tests.channels.testbed import ChannelsTestbed
from tests.channels.voice_setup import ASSISTANT_LINE, CALLER, VoiceSetup

TWILIO_AUTH_TOKEN: str = "test-token-0000"
TWILIO_SETTINGS: dict[str, str] = {
    "TWILIO_ACCOUNT_SID": "AC" + "0" * 32,
    "TWILIO_AUTH_TOKEN": TWILIO_AUTH_TOKEN,
    "TWILIO_FROM_NUMBER": "+15005550006",
}
STAFF_MOBILE: str = "+995555123456"
CALL_SID: str = "CA" + "0" * 31 + "1"
FORM: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}


def fallback_path(business_id: BusinessId | str) -> str:
    """The business's call fallback (its rented numbers' VoiceFallbackUrl)."""

    return f"/v1/telephony/twilio/voice-fallback/{business_id}"


def dial_path(business_id: BusinessId | str) -> str:
    """Where Twilio reports how the call put through to staff ended."""

    return f"{fallback_path(business_id)}/dial-status"


def fallback_settings(**overrides: str) -> AppSettings:
    return build_settings(**{**TWILIO_SETTINGS, **overrides})


def build_fallback_client(testbed: ChannelsTestbed) -> TestClient:
    """The fallback router over the testbed's missed-call flow and outbox."""

    adapter = TwilioCallFallbackAdapter(testbed.settings)
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_twilio_voice_router(
            call_fallback_operator=wrap(
                CallFallbackOrchestrator(
                    RouteCallFallbackUseCase(
                        adapter,
                        testbed.business_repo,
                        testbed.profile_repo,
                        testbed.phone_number_parser,
                        testbed.wall_clock,
                    ),
                    NotifyCallFallbackUseCase(
                        testbed.business_repo,
                        testbed.call_staff_alerts,
                        testbed.text_resolver,
                        testbed.phone_number_parser,
                    ),
                    testbed.missed_calls,
                )
            ),
            fallback_dial_operator=wrap(
                FallbackDialOrchestrator(
                    ReadFallbackDialUseCase(adapter, testbed.wall_clock),
                    testbed.missed_calls,
                )
            ),
        )
    )
    return TestClient(http_application)


def set_staff_mobile(setup: VoiceSetup, number: str | None = STAFF_MOBILE) -> None:
    """The profile's phone for calls that need a person."""

    setup.testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=setup.business.id,
            niche_key=NicheKey.ENTERTAINMENT,
            answers_language=LanguageTag("ka"),
            contacts=BusinessContacts(
                handoff_phone_number=(
                    None if number is None else E164PhoneNumber(number)
                )
            ),
        )
    )


def fallback_form(
    caller: str = CALLER,
    called: str = ASSISTANT_LINE,
    call_sid: str = CALL_SID,
    forwarded_from: str | None = None,
) -> dict[str, str]:
    """Twilio's fallback request after the voice platform failed the call."""

    fields: dict[str, str] = {
        "AccountSid": TWILIO_SETTINGS["TWILIO_ACCOUNT_SID"],
        "CallSid": call_sid,
        "CallStatus": "ringing",
        "Direction": "inbound",
        "From": caller,
        "To": called,
        "ErrorCode": "11200",
        "ErrorUrl": "https://api.us.elevenlabs.io/twilio/inbound_call",
    }
    if forwarded_from is not None:
        fields["ForwardedFrom"] = forwarded_from
    return fields


def dial_form(status: str, call_sid: str = CALL_SID) -> dict[str, str]:
    """Twilio's report of how the call to the staff mobile ended."""

    return {
        **fallback_form(call_sid=call_sid),
        "CallStatus": "in-progress",
        "DialCallSid": "CA" + "0" * 31 + "2",
        "DialCallStatus": status,
        "DialCallDuration": "0",
    }


def sign_twilio(
    path: str, fields: dict[str, str], token: str = TWILIO_AUTH_TOKEN
) -> str:
    """Twilio's signature: HMAC-SHA1 of the URL and the sorted fields."""

    signed: str = (
        APP_BASE_URL + path + "".join(name + fields[name] for name in sorted(fields))
    )
    digest: bytes = hmac.new(
        token.encode("utf-8"), signed.encode("utf-8"), hashlib.sha1
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def post_twilio(
    setup: VoiceSetup,
    path: str,
    fields: dict[str, str],
    signature: str | None = "valid",
) -> HttpResponse:
    headers: dict[str, str] = dict(FORM)
    if signature == "valid":
        headers["X-Twilio-Signature"] = sign_twilio(path, fields)
    elif signature is not None:
        headers["X-Twilio-Signature"] = signature
    response = build_fallback_client(setup.testbed).post(
        path, content=urlencode(fields).encode("utf-8"), headers=headers
    )
    setup.testbed.run_worker()
    return response
