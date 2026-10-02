"""The post-call webhook stores each call outcome, bills it and confirms bookings."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.bookings import BookingStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.handoffs.strings import HandoffSummary
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import TELEGRAM_BOT_TOKEN
from tests.channels.post_call_steps import (
    add_booking,
    post_call_payload,
    process_call,
    stored_calls,
)
from tests.channels.voice_setup import ASSISTANT_LINE, CALLER, build_voice_setup


class TestPostCallWebhook:
    def test_booking_call_is_stored_billed_and_confirmed(self) -> None:
        setup = build_voice_setup()
        setup.testbed.add_channel(
            setup.business.id,
            ChannelKind.TELEGRAM,
            "funicular_vr_bot",
            TELEGRAM_BOT_TOKEN,
        )
        setup.testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", telegram_ok({})
        )
        add_booking(setup)

        body = process_call(setup, post_call_payload(tool_names=("create_booking",)))

        assert body["status"] == "recorded"
        assert body["outcome"] == "booking"
        assert body["is_confirmation_sent"] is True
        [call] = stored_calls(setup)
        assert str(call.id) == body["call_id"]
        assert call.conversation_id == setup.conversation.id
        assert call.from_phone_number == CALLER
        assert call.to_phone_number == ASSISTANT_LINE
        assert call.started_at == 1_790_855_000_000_000
        assert call.duration_seconds == 95
        assert call.cost_micro_usd == 152_300
        assert call.recording_path == "elevenlabs/conversations/conv_1"
        assert call.transcript == (
            "[00:00] assistant: გამარჯობა! AI ასისტენტი.\n"
            "[01:05] customer: მაგიდა ოთხისთვის"
        )
        [usage] = setup.testbed.usage_event_repo.list_by_business_between(
            setup.business.id, Microseconds(0), Microseconds(2**62)
        )
        assert usage.kind is UsageKind.VOICE_SECONDS
        assert usage.quantity == 95
        assert usage.cost_micro_usd == 152_300
        assert ("create", "call") in setup.testbed.audit_actions(setup.business.id)
        [sent] = setup.testbed.telegram_transport.requests_to("/sendMessage")
        assert sent.json()["chat_id"] == "555000111"
        text: str = sent.json()["text"]
        assert text.startswith("Funicular VR: თქვენი ჯავშანი დადასტურებულია")
        assert "19:30" in text
        assert "სტუმრები: 4." in text

    def test_confirmation_falls_back_to_the_next_messenger(self) -> None:
        setup = build_voice_setup(conversation_language="ru")
        setup.testbed.add_channel(
            setup.business.id,
            ChannelKind.TELEGRAM,
            "funicular_vr_bot",
            TELEGRAM_BOT_TOKEN,
        )
        setup.testbed.add_channel(
            setup.business.id, ChannelKind.WHATSAPP, "106540352242922"
        )
        setup.testbed.telegram_transport.respond(
            "POST",
            r"/sendMessage$",
            {"ok": False, "error_code": 403, "description": "blocked"},
            status_code=403,
        )
        setup.testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})
        add_booking(setup, party_size=1)

        body = process_call(setup, post_call_payload())

        assert body["is_confirmation_sent"] is True
        [whatsapp] = setup.testbed.meta_transport.requests
        message: str = whatsapp.json()["text"]["body"]
        assert message.startswith("Funicular VR: ваша бронь на ")
        assert "Гостей" not in message

    def test_no_reachable_messenger_means_no_confirmation(self) -> None:
        setup = build_voice_setup()
        add_booking(setup)

        body = process_call(setup, post_call_payload())

        assert body["outcome"] == "booking"
        assert body["is_confirmation_sent"] is False

    def test_cancelled_bookings_do_not_count(self) -> None:
        setup = build_voice_setup()
        booking = add_booking(setup)
        booking.status = BookingStatus.CANCELLED
        setup.testbed.booking_repo.save(booking)

        assert process_call(setup, post_call_payload())["outcome"] == "information"

    def test_lead_handoff_and_unanswered_outcomes(self) -> None:
        lead_setup = build_voice_setup()
        lead_setup.testbed.lead_repo.save(
            LeadDocument(
                business_id=lead_setup.business.id,
                contact_id=lead_setup.contact.id,
                conversation_id=lead_setup.conversation.id,
                lead_type=LeadType.BANQUET,
                details=LeadDetails("Banquet for 40"),
                source_channel=ChannelKind.PHONE,
            )
        )
        handoff_setup = build_voice_setup()
        handoff_setup.testbed.handoff_repo.save(
            HandoffDocument(
                business_id=handoff_setup.business.id,
                conversation_id=handoff_setup.conversation.id,
                contact_id=handoff_setup.contact.id,
                reason=HandoffReason.COMPLAINT,
                summary=HandoffSummary("Complaint"),
            )
        )
        question_setup = build_voice_setup()

        assert process_call(lead_setup, post_call_payload())["outcome"] == "lead"
        assert process_call(handoff_setup, post_call_payload())["outcome"] == "handoff"
        assert (
            process_call(
                question_setup,
                post_call_payload(tool_names=("record_unanswered_question", "unknown")),
            )["outcome"]
            == "unanswered_question"
        )

    def test_information_and_abandoned_calls(self) -> None:
        setup = build_voice_setup()

        short = process_call(setup, post_call_payload("conv_short", duration=4))
        silent = process_call(
            setup, post_call_payload("conv_silent", caller_spoke=False)
        )
        informative = process_call(setup, post_call_payload("conv_info"))

        assert short["outcome"] == "abandoned"
        assert silent["outcome"] == "abandoned"
        assert informative["outcome"] == "information"
        assert all(call.conversation_id is None for call in stored_calls(setup)[:2])
