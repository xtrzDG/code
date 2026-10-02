"""The links the phone assistant promised are texted to the caller after the call."""

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.conversations import MessageDocument, ToolCallRecord
from app.schemas.domain.profiles import (
    BusinessAddress,
    BusinessLink,
    BusinessProfileDocument,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.call_links import read_promised_kind
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import TELEGRAM_BOT_TOKEN
from tests.channels.post_call_steps import post_call, post_call_payload, stored_calls
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

MENU_URL: str = "https://funicular.example/menu"
MAPS_URL: str = "https://maps.example.com/funicular"


def links_setup(*, with_telegram: bool = True) -> VoiceSetup:
    setup = build_voice_setup()
    setup.testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=setup.business.id,
            niche_key=NicheKey.ENTERTAINMENT,
            answers_language=LanguageTag("ka"),
            address=BusinessAddress(
                text=AddressText("Funicular, Tbilisi"), maps_url=WebLink(MAPS_URL)
            ),
            links=[BusinessLink(kind=BusinessLinkKind.MENU, url=WebLink(MENU_URL))],
        )
    )
    if with_telegram:
        setup.testbed.add_channel(
            setup.business.id,
            ChannelKind.TELEGRAM,
            "funicular_vr_bot",
            TELEGRAM_BOT_TOKEN,
        )
        setup.testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", telegram_ok({})
        )
    return setup


def record_send_link(setup: VoiceSetup, kind: str, *, promised: bool = True) -> None:
    now = setup.testbed.clock.now_microseconds()
    texted = "true" if promised else "false"
    setup.testbed.message_repo.save(
        MessageDocument(
            conversation_id=setup.conversation.id,
            business_id=setup.business.id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.SYSTEM,
            text=MessageText("Voice agent called send_link."),
            tool_calls=[
                ToolCallRecord(
                    tool_name=AssistantToolName.SEND_LINK,
                    input_json=LlmToolInputJson(f'{{"kind":"{kind}"}}'),
                    result_json=LlmToolResultJson(
                        f'{{"kind":"{kind}","texted_after_call":{texted}}}'
                    ),
                )
            ],
            created_at=now,
            updated_at=now,
        )
    )


def test_promised_links_are_texted_once_in_the_call_language() -> None:
    setup = links_setup()
    record_send_link(setup, "menu")
    record_send_link(setup, "map")
    record_send_link(setup, "menu")

    response = post_call(setup, post_call_payload(tool_names=("send_link",)))

    assert response.status_code == 200
    [sent] = setup.testbed.telegram_transport.requests_to("/sendMessage")
    assert sent.json()["chat_id"] == "555000111"
    assert sent.json()["text"] == (
        f"Funicular VR: ბმულები თქვენი ზარიდან.\n{MENU_URL}\n{MAPS_URL}"
    )


def test_links_that_were_not_promised_or_do_not_exist_are_not_sent() -> None:
    setup = links_setup()
    record_send_link(setup, "menu", promised=False)
    record_send_link(setup, "payment")

    post_call(setup, post_call_payload(tool_names=("send_link",)))

    assert setup.testbed.telegram_transport.requests_to("/sendMessage") == []


def test_no_messenger_reaches_the_caller_and_the_call_is_still_stored() -> None:
    setup = links_setup(with_telegram=False)
    record_send_link(setup, "menu")

    response = post_call(setup, post_call_payload(tool_names=("send_link",)))

    assert response.json()["status"] == "recorded"
    assert len(stored_calls(setup)) == 1


def test_a_failing_messenger_does_not_break_the_call_or_send_twice() -> None:
    setup = links_setup()
    setup.testbed.telegram_transport.respond(
        "POST",
        r"/sendMessage$",
        {"ok": False, "error_code": 403, "description": "blocked"},
        status_code=403,
    )
    record_send_link(setup, "menu")
    payload = post_call_payload(tool_names=("send_link",))

    first = post_call(setup, payload)
    repeated = post_call(setup, payload)

    assert first.json()["status"] == "recorded"
    assert repeated.json()["status"] == "duplicate"
    assert len(setup.testbed.telegram_transport.requests_to("/sendMessage")) == 1


@pytest.mark.parametrize(
    ("result_json", "kind"),
    [
        ('{"kind":"menu","texted_after_call":true}', BusinessLinkKind.MENU),
        ('{"kind":"menu","texted_after_call":false}', None),
        ('{"kind":"menu","url":"https://x"}', None),
        ('{"kind":"poster","texted_after_call":true}', None),
        ('{"kind":7,"texted_after_call":true}', None),
        ("[1, 2]", None),
        ("not json", None),
    ],
)
def test_only_a_result_that_promised_a_text_counts(
    result_json: str, kind: BusinessLinkKind | None
) -> None:
    assert read_promised_kind(result_json) is kind
