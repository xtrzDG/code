"""
Twilio Programmable Messaging as the SMS fallback uses it: the form the
platform posts matches Twilio's specification with every field known, the
documented Message answer matches it, and Twilio's documented errors become
the errors the delivery flow relies on.
"""

from typing import Any
from urllib.parse import parse_qsl

import pytest

from app.clients.twilio.twilio_messaging_client import TwilioMessagingClient
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.constrained_strings import (
    SmsSenderId,
    TwilioAccountSid,
    TwilioMessagingServiceSid,
)
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.strings import PlatformSecret
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "twilio_messaging_api.json"
ACCOUNT = TwilioAccountSid("AC" + "0" * 32)
MESSAGES_PATH: str = r"/Accounts/AC0+/Messages\.json$"
TEXT = SmsMessageText("Funicular VR: we could not take your call. Reply here to book.")


def client(
    transport: RecordingTransport, through_service: bool = True
) -> TwilioMessagingClient:
    return TwilioMessagingClient(
        account_sid=ACCOUNT,
        auth_token=PlatformSecret("test-token-0000"),
        sender=None if through_service else SmsSenderId("+12025550123"),
        messaging_service_sid=(
            TwilioMessagingServiceSid("MG" + "0" * 32) if through_service else None
        ),
        transport=transport.build(),
    )


def test_message_answer_matches_the_specification() -> None:
    assert_inbound(
        load_json_fixture("twilio", "message_created.json"),
        SPEC,
        "response:messages.create",
    )


@pytest.mark.parametrize("through_service", [True, False])
def test_sms_form_matches_the_specification(through_service: bool) -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST", MESSAGES_PATH, load_json_fixture("twilio", "message_created.json"), 201
    )

    client(transport, through_service).send_sms(E164PhoneNumber("+995599123456"), TEXT)

    [request] = transport.requests
    form: dict[str, str] = dict(parse_qsl(request.body.decode()))
    assert_outbound(form, SPEC, "request:messages.create")
    assert ("MessagingServiceSid" in form) is through_service


@pytest.mark.parametrize(
    "case",
    load_json_fixture("twilio", "twilio_errors.json")["cases"],
    ids=lambda case: f"{case['status']}-{case['body']['code']}",
)
def test_documented_errors_become_delivery_errors(case: dict[str, Any]) -> None:
    transport = RecordingTransport()
    transport.respond("POST", MESSAGES_PATH, case["body"], case["status"])

    with pytest.raises(ApplicationError) as raised:
        client(transport).send_sms(E164PhoneNumber("+995599123456"), TEXT)

    assert type(raised.value).__name__ == case["expected"]
    # Twilio's code is named; the recipient never is.
    assert "+995599123456" not in str(raised.value)
