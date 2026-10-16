"""
Callers the phone assistant could not help are texted back: a silent
caller, a transfer nobody picked up, a call the voice platform could not
start. The caller's reply continues the WhatsApp conversation.
"""

from typing import Any

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackChannel,
    TextBackStatus,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from tests.calls.call_steps import (
    TEMPLATE_NAME,
    add_staff_chat,
    connect_whatsapp,
    failed_start_payload,
    missed_calls,
    save_call_settings,
    staff_texts,
    whatsapp_templates,
)
from tests.channels.meta_payloads import post_meta, whatsapp_message, whatsapp_webhook
from tests.channels.post_call_steps import post_call, post_call_payload, process_call
from tests.channels.voice_setup import VoiceSetup, build_voice_setup


def transfer_payload(result_value: str, is_error: bool = False) -> dict[str, Any]:
    """The caller asked for a person; the transfer tool reported `result_value`."""

    payload = post_call_payload("conv_transfer", tool_names=("transfer_to_number",))
    [first, _] = payload["data"]["transcript"]
    first["tool_results"] = [
        {
            "request_id": "r0",
            "tool_name": "transfer_to_number",
            "result_value": result_value,
            "is_error": is_error,
        }
    ]
    return payload


def texting_setup() -> VoiceSetup:
    setup = build_voice_setup()
    save_call_settings(setup)
    connect_whatsapp(setup)
    return setup


class TestSilentCallers:
    def test_a_silent_caller_gets_the_whatsapp_template(self) -> None:
        setup = texting_setup()

        process_call(setup, post_call_payload(caller_spoke=False))

        [missed] = missed_calls(setup)
        assert missed.reason is MissedCallReason.NO_SPEECH
        assert missed.source is MissedCallSource.VOICE_PLATFORM
        assert str(missed.provider_call_id) == "conv_1"
        assert missed.caller_phone_number == "+995599123456"
        assert str(missed.language) == "ka"
        assert missed.status is TextBackStatus.SENT
        assert missed.channel is TextBackChannel.WHATSAPP
        assert missed.call_id is not None
        [template] = whatsapp_templates(setup)
        assert template["to"] == "995599123456"
        assert template["template"]["name"] == TEMPLATE_NAME
        assert template["template"]["language"]["code"] == "ka"
        [component] = template["template"]["components"]
        assert component["parameters"] == [{"type": "text", "text": "Funicular VR"}]

    def test_the_text_back_opens_the_whatsapp_conversation(self) -> None:
        setup = texting_setup()

        process_call(setup, post_call_payload(caller_spoke=False))

        [missed] = missed_calls(setup)
        assert missed.conversation_id is not None
        conversation = setup.testbed.conversation_repo.get(
            setup.business.id, missed.conversation_id
        )
        assert conversation is not None
        assert conversation.channel is ChannelKind.WHATSAPP
        assert str(conversation.channel_user_id) == "995599123456"
        assert conversation.contact_id == setup.contact.id
        [message] = setup.testbed.message_repo.list_by_conversation(
            setup.business.id, conversation.id
        )
        assert message.author is MessageAuthor.STAFF
        assert message.direction is MessageDirection.OUTBOUND
        assert "Funicular VR" in str(message.text)

        post_meta(
            setup.testbed,
            whatsapp_webhook([whatsapp_message("995599123456", "გამარჯობა")]),
        )
        setup.testbed.run_worker()

        replies = [
            message
            for message in setup.testbed.message_repo.list_by_conversation(
                setup.business.id, conversation.id
            )
            if message.author is MessageAuthor.CUSTOMER
        ]
        assert [str(reply.text) for reply in replies] == ["გამარჯობა"]

    def test_a_caller_who_spoke_is_not_texted(self) -> None:
        setup = texting_setup()

        process_call(setup, post_call_payload())

        assert missed_calls(setup) == []
        assert whatsapp_templates(setup) == []

    def test_a_late_report_is_stored_but_not_texted(self) -> None:
        setup = texting_setup()
        setup.testbed.clock.advance(3 * 60 * 60)

        process_call(setup, post_call_payload(caller_spoke=False))

        [missed] = missed_calls(setup)
        assert missed.status is TextBackStatus.SKIPPED
        assert str(missed.skip_reason) == "too_late"
        assert whatsapp_templates(setup) == []


class TestTransfers:
    def test_a_transfer_nobody_answered_is_a_missed_call(self) -> None:
        setup = texting_setup()

        process_call(setup, transfer_payload("Transfer failed: no-answer"))

        [missed] = missed_calls(setup)
        assert missed.reason is MissedCallReason.TRANSFER_UNANSWERED
        assert missed.status is TextBackStatus.SENT

    def test_a_transfer_error_is_a_missed_call(self) -> None:
        setup = texting_setup()

        process_call(setup, transfer_payload("", is_error=True))

        [missed] = missed_calls(setup)
        assert missed.reason is MissedCallReason.TRANSFER_UNANSWERED

    def test_a_connected_transfer_is_not(self) -> None:
        setup = texting_setup()
        payload = transfer_payload("Transferred to +995 32 2 00 00 01")
        # The caller spoke before the transfer, and nothing came after it.
        payload["data"]["transcript"].reverse()

        process_call(setup, payload)

        assert missed_calls(setup) == []


class TestFailedStarts:
    def test_a_call_the_platform_could_not_start_is_texted_and_reported(
        self,
    ) -> None:
        setup = texting_setup()
        add_staff_chat(setup, language="en")

        response = post_call(setup, failed_start_payload())

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "recorded"
        [missed] = missed_calls(setup)
        assert missed.reason is MissedCallReason.NOT_STARTED
        assert str(missed.provider_call_id) == "conv_failed"
        assert missed.called_at == 1_790_855_900_000_000
        assert missed.status is TextBackStatus.SENT
        [text] = staff_texts(setup)
        lines = str(text.text).split("\n")
        assert lines[0] == "Missed call · Funicular VR"
        assert lines[2] == "Why: the assistant could not take the call"
        assert lines[3].startswith("We wrote to the caller on WhatsApp")

    def test_the_same_failure_twice_is_handled_once(self) -> None:
        setup = texting_setup()
        add_staff_chat(setup, language="en")
        post_call(setup, failed_start_payload())

        again = post_call(setup, failed_start_payload())

        assert again.json()["status"] == "duplicate"
        assert len(missed_calls(setup)) == 1
        assert len(whatsapp_templates(setup)) == 1
        assert len(staff_texts(setup)) == 1

    def test_a_line_no_business_has_is_ignored(self) -> None:
        setup = texting_setup()

        response = post_call(setup, failed_start_payload(called="+995322999999"))

        assert response.json()["status"] == "ignored"
        assert missed_calls(setup) == []

    def test_a_forged_failure_is_refused(self) -> None:
        setup = texting_setup()

        response = post_call(setup, failed_start_payload(), signature="t=1,v0=bad")

        assert response.status_code == 401
        assert missed_calls(setup) == []
