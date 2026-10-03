"""After every call staff get its summary: written once, in their language."""

import json

from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.dto.calls.call_summaries import CallSummaryRequest
from app.schemas.dto.voice_webhooks import RecordedCall
from tests.calls.call_steps import (
    add_staff_chat,
    save_call_settings,
    staff_texts,
)
from tests.channels.channels_settings import build_settings
from tests.channels.post_call_steps import (
    add_booking,
    post_call_payload,
    process_call,
    stored_calls,
)
from tests.channels.voice_setup import build_voice_setup

SUMMARIES: str = json.dumps(
    {
        "ka": "სტუმარს ოთხი ადგილი სურს შაბათს.",
        "ru": "Гость хочет столик на четверых в субботу.",
        "en": "Not requested.",
    },
    ensure_ascii=False,
)


class TestCallSummary:
    def test_staff_get_the_summary_in_their_language(self) -> None:
        setup = build_voice_setup()
        add_staff_chat(setup, language="ru")
        setup.testbed.summary_answers.append(f"Here you go: {SUMMARIES}")

        process_call(setup, post_call_payload())

        [call] = stored_calls(setup)
        assert call.summarized_at is not None
        assert {
            str(summary.language): str(summary.text) for summary in call.summaries
        } == {
            "ka": "სტუმარს ოთხი ადგილი სურს შაბათს.",
            "ru": "Гость хочет столик на четверых в субботу.",
        }
        [request] = setup.testbed.summary_requests
        assert request.effort is LlmEffort.LOW
        assert request.model_id == setup.testbed.settings.llm_model_id
        assert "Languages: ka, ru" in str(request.transcript)
        [text] = staff_texts(setup)
        assert text.staff_contact is not None
        assert str(text.staff_contact.address) == "-100555"
        lines = str(text.text).split("\n")
        assert lines[0] == "Итог звонка · Funicular VR"
        assert lines[1].startswith("Звонил: +995 599 12 34 56 · ")
        assert lines[1].endswith("1 мин 35 с")
        assert lines[2] == "Гость хочет столик на четверых в субботу."
        assert lines[3] == "Итог: дана информация"

    def test_a_booking_call_names_the_booking(self) -> None:
        setup = build_voice_setup()
        add_staff_chat(setup, language="en")
        add_booking(setup)
        setup.testbed.summary_answers.append(SUMMARIES)

        process_call(setup, post_call_payload(tool_names=("create_booking",)))

        [text] = staff_texts(setup)
        assert "Result: booking made" in str(text.text)
        assert "Booking: " in str(text.text)
        assert "guests: 4" in str(text.text)

    def test_the_summary_is_written_and_sent_once(self) -> None:
        setup = build_voice_setup()
        add_staff_chat(setup, language="ru")
        setup.testbed.summary_answers.extend([SUMMARIES, SUMMARIES])
        process_call(setup, post_call_payload())
        [call] = stored_calls(setup)
        first_summaries = list(call.summaries)

        outcome = setup.testbed.summarize_call.run(
            CallSummaryRequest(
                call=RecordedCall(
                    status=PostCallEventStatus.RECORDED,
                    business_id=setup.business.id,
                    call_id=call.id,
                    conversation_id=call.conversation_id,
                ),
                transcript=[],
            )
        )

        assert outcome.is_generated is False
        assert len(setup.testbed.summary_requests) == 1
        [stored] = stored_calls(setup)
        assert stored.summaries == first_summaries
        assert len(staff_texts(setup)) == 1

    def test_summaries_turned_off_send_nothing(self) -> None:
        setup = build_voice_setup()
        add_staff_chat(setup)
        save_call_settings(setup, is_summary_enabled=False, is_text_back_enabled=False)
        setup.testbed.summary_answers.append(SUMMARIES)

        process_call(setup, post_call_payload())

        [call] = stored_calls(setup)
        assert call.summarized_at is None
        assert setup.testbed.summary_requests == []
        assert staff_texts(setup) == []

    def test_a_model_failure_still_sends_the_facts(self) -> None:
        setup = build_voice_setup()
        add_staff_chat(setup, language="ru")

        process_call(setup, post_call_payload())

        [call] = stored_calls(setup)
        assert call.summaries == []
        assert call.summarized_at is not None
        [text] = staff_texts(setup)
        assert str(text.text).split("\n")[2] == "Итог: дана информация"

    def test_an_unreadable_answer_leaves_no_summary(self) -> None:
        setup = build_voice_setup()
        add_staff_chat(setup, language="ru")
        setup.testbed.summary_answers.append("I cannot summarize this call.")

        process_call(setup, post_call_payload())

        [call] = stored_calls(setup)
        assert call.summaries == []
        assert len(staff_texts(setup)) == 1

    def test_the_cheap_model_is_used_when_configured(self) -> None:
        setup = build_voice_setup(
            settings=build_settings(LLM_SUMMARY_MODEL_ID="gpt-5-nano")
        )
        setup.testbed.summary_answers.append(SUMMARIES)

        process_call(setup, post_call_payload())

        [request] = setup.testbed.summary_requests
        assert str(request.model_id) == "gpt-5-nano"
        # The owner's language only: no staff chat speaks another one.
        [call] = stored_calls(setup)
        assert [str(summary.language) for summary in call.summaries] == ["ka"]

    def test_summaries_reach_linked_chats_only(self) -> None:
        setup = build_voice_setup()
        add_staff_chat(setup, language="ru")
        add_staff_chat(
            setup,
            language="en",
            channel=ManagerContactChannel.EMAIL,
            address="nino@example.com",
        )
        setup.testbed.summary_answers.append(SUMMARIES)

        process_call(setup, post_call_payload())

        [text] = staff_texts(setup)
        assert text.staff_contact is not None
        assert text.staff_contact.channel is ManagerContactChannel.TELEGRAM

    def test_a_silent_caller_is_reported_as_missed(self) -> None:
        setup = build_voice_setup()
        add_staff_chat(setup, language="ru")
        add_staff_chat(
            setup,
            language="en",
            channel=ManagerContactChannel.EMAIL,
            address="nino@example.com",
        )

        process_call(setup, post_call_payload(caller_spoke=False))

        # Nothing to summarize; every channel hears so someone calls back.
        assert setup.testbed.summary_requests == []
        texts = staff_texts(setup)
        assert len(texts) == 2
        telegram = next(
            text
            for text in texts
            if text.staff_contact is not None
            and text.staff_contact.channel is ManagerContactChannel.TELEGRAM
        )
        lines = str(telegram.text).split("\n")
        assert lines[0] == "Пропущенный звонок · Funicular VR"
        assert lines[2] == "Причина: положил трубку, ничего не сказав"
        assert lines[3].startswith("Звонившему мы не написали (")
