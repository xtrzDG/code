"""
What the platform sends to Meta outside a customer reply (templates, the
login code, typing signals, media lookups) matches the vendor's
specification with every object closed, and Meta's documented answers and
errors are read as the platform expects.
"""

from typing import Any

import pytest

from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.meta.meta_media_client import MetaMediaClient
from app.clients.meta.meta_typing_client import MetaTypingClient
from app.clients.meta.whatsapp_authentication_client import (
    WhatsAppAuthenticationClient,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    OutboundMessagePart,
    ProviderMessageId,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.media.strings import ProviderMediaId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import OtpCode
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.meta.meta_cases import PAGES_SPEC, WHATSAPP_SPEC
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

TOKEN = PlatformSecret("test-token-0000")
PHONE_NUMBER_ID = MetaObjectId("106540352242922")
CUSTOMER = ChannelUserId("16505551234")


def answering_transport() -> RecordingTransport:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/\d+/messages$",
        load_json_fixture("meta", "whatsapp_send_response.json"),
    )
    transport.respond(
        "POST",
        r"/me/messages$",
        load_json_fixture("meta", "messenger_send_response.json"),
    )
    return transport


def test_template_message_matches_the_spec() -> None:
    transport = answering_transport()
    client = MetaGraphClient(transport=transport.build())

    message_id = client.send_whatsapp_template(
        TOKEN,
        PHONE_NUMBER_ID,
        CUSTOMER,
        WhatsAppTemplateName("booking_reminder"),
        WhatsAppTemplateLanguageCode("ka"),
        [OutboundMessagePart("Nino"), OutboundMessagePart("19:00")],
    )

    [request] = transport.requests
    assert_outbound(request.json(), WHATSAPP_SPEC, "request:messages.send")
    assert message_id == "wamid.HBgLMTY1MDUwNzY1MjAVAgARGBI5QTNDQTVCM0Q0Q0Q2RTY3RTcA"


def test_login_code_template_matches_the_spec() -> None:
    transport = answering_transport()
    client = WhatsAppAuthenticationClient(
        access_token=TOKEN,
        phone_number_id=PHONE_NUMBER_ID,
        template_name=WhatsAppTemplateName("login_code"),
        transport=transport.build(),
    )

    client.send_authentication_code(
        E164PhoneNumber("+995599123456"),
        OtpCode("482915"),
        WhatsAppTemplateLanguageCode("en"),
    )

    [request] = transport.requests
    assert_outbound(request.json(), WHATSAPP_SPEC, "request:messages.send")


def test_typing_signals_match_the_specs() -> None:
    transport = answering_transport()
    client = MetaTypingClient(transport=transport.build())

    client.show_whatsapp_typing(
        TOKEN, PHONE_NUMBER_ID, ProviderMessageId("wamid.customer-0001")
    )
    client.show_page_typing(TOKEN, ChannelUserId("7034567890123456"))

    whatsapp, page = transport.requests
    assert_outbound(whatsapp.json(), WHATSAPP_SPEC, "MarkMessageRequestPayload")
    assert_outbound(page.json(), PAGES_SPEC, "request:messages.send")


def test_media_url_answer_matches_the_spec_and_is_read() -> None:
    answer: dict[str, Any] = load_json_fixture("meta", "whatsapp_media_url.json")
    assert_inbound(answer, WHATSAPP_SPEC, "response:media.get")
    transport = RecordingTransport()
    transport.respond("GET", r"/1150482956743210$", answer)

    media = MetaMediaClient(transport=transport.build()).read_whatsapp_media(
        TOKEN, ProviderMediaId("1150482956743210")
    )

    assert str(media.url).startswith("https://lookaside.fbsbx.com/")
    assert media.mime_type == "audio/ogg"
    # Meta documents the size as a string of digits.
    assert media.file_size == 21480


@pytest.mark.parametrize(
    "case",
    load_json_fixture("meta", "graph_api_errors.json")["cases"],
    ids=lambda case: f"{case['status']}-{case['body']['error']['code']}",
)
def test_graph_api_errors_become_application_errors(case: dict[str, Any]) -> None:
    transport = RecordingTransport()
    transport.respond("POST", r"/\d+/messages$", case["body"], case["status"])
    client = MetaGraphClient(transport=transport.build())

    with pytest.raises(ApplicationError) as raised:
        client.send_whatsapp_text(
            TOKEN, PHONE_NUMBER_ID, CUSTOMER, OutboundMessagePart("Hello")
        )

    assert type(raised.value).__name__ == case["expected"]
