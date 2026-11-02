"""
A caller who reads a card number to the voice agent: the transcript, its
summary for staff and the transcript of a declined recording keep it
masked, like a voice note in a chat, and the call's audio is not kept even
where the business records calls (PAY-05, VOICE-10). An account or ID
number alone leaves a recorded call's audio, masked in its transcript.
"""

from typing import Any

from tests.calls.call_steps import add_staff_chat, save_call_settings
from tests.channels.post_call_steps import post_call_payload, process_call, stored_calls
from tests.channels.telegram_updates import connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed
from tests.channels.voice_setup import build_voice_setup
from tests.media.inbound_media_steps import read_attachments, telegram_update
from tests.media.media_fakes import ogg_opus_bytes

CARD_MESSAGE: str = "4242 4242 4242 4242 cvv 123"
MASKED_MESSAGE: str = "[card number] cvv [security code]"
SAID_CARD: str = (
    f"My card is {CARD_MESSAGE}, IBAN IT60 X054 2811 1010 0000 0123 456, "
    "for Saturday at 19:00, call me on +995 599 12 34 56."
)
SAID_ACCOUNT: str = (
    "IBAN IT60 X054 2811 1010 0000 0123 456, codice fiscale RSSMRA85T10A562S, "
    "call me on +995 599 12 34 56."
)
PLATFORM_COPY: str = "elevenlabs/conversations/conv_1"


def card_payload(said: str, *, declined: bool) -> dict[str, Any]:
    payload = post_call_payload(tool_names=("decline_recording",) if declined else ())
    payload["data"]["transcript"].append(
        {"role": "user", "message": said, "time_in_call_secs": 80}
    )
    return payload


def test_a_recorded_call_keeps_no_card_in_its_transcript_summary_or_audio() -> None:
    setup = build_voice_setup()
    save_call_settings(setup, is_recording_enabled=True)
    add_staff_chat(setup, language="en")
    setup.testbed.summary_answers.append('{"ka": "ზარი.", "en": "A call."}')

    process_call(setup, card_payload(SAID_CARD, declined=False))

    [call] = stored_calls(setup)
    transcript = str(call.transcript)
    assert f"My card is {MASKED_MESSAGE}, IBAN [account number]" in transcript
    assert "4242" not in transcript and "cvv 123" not in transcript
    assert "for Saturday at 19:00" in transcript
    [request] = setup.testbed.summary_requests
    asked = str(request.transcript)
    assert "4242" not in asked and "IT60" not in asked
    assert "[card number]" in asked
    # The audio would keep the card: the call keeps none, as if declined.
    assert call.recording_declined is True
    assert call.recording_path is None
    assert setup.testbed.recording_storage.deleted == [PLATFORM_COPY]


def test_a_recorded_call_with_an_account_number_keeps_its_audio_masked() -> None:
    setup = build_voice_setup()
    save_call_settings(setup, is_recording_enabled=True)

    process_call(setup, card_payload(SAID_ACCOUNT, declined=False))

    [call] = stored_calls(setup)
    assert call.recording_declined is False
    assert str(call.recording_path) == PLATFORM_COPY
    transcript = str(call.transcript)
    assert "IBAN [account number], codice fiscale [id number]" in transcript
    assert "IT60" not in transcript and "RSSMRA85T10A562S" not in transcript
    # The rest of what was said stays for staff, the phone number too.
    assert "call me on +995 599 12 34 56." in transcript


def test_a_declined_recording_masks_the_card_and_the_phone() -> None:
    setup = build_voice_setup()

    process_call(setup, card_payload(SAID_CARD, declined=True))

    [call] = stored_calls(setup)
    transcript = str(call.transcript)
    assert MASKED_MESSAGE in transcript and "[phone]" in transcript
    assert "4242" not in transcript and "599 12 34 56" not in transcript


def test_a_voice_note_with_a_card_is_kept_masked() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes(seconds=7)
    testbed.voice_transcriber.texts = [f"La mia carta è {CARD_MESSAGE}"]

    post_update(testbed, channel, telegram_update(0))
    testbed.run_worker()

    [voice] = read_attachments(testbed)
    assert str(voice.transcript) == f"La mia carta è {MASKED_MESSAGE}"
    assert voice.media_id is not None
    stored = testbed.message_media_repo.get(business.id, voice.media_id)
    assert stored is not None and str(stored.transcript) == str(voice.transcript)
