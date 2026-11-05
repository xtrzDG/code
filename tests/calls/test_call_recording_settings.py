"""
Recording is off unless the owner turns it on, and the staff part of a
transferred call is never kept: no audio, transcript or evaluation of it.
"""

from typing import Any

from app.schemas.domain.conversations import CallDocument
from tests.calls.call_steps import save_call_settings
from tests.channels.post_call_steps import post_call_payload, process_call, stored_calls
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

PLATFORM_COPY: str = "elevenlabs/conversations/conv_1"
STAFF_LINE: str = "Hi, this is Giorgi from the front desk, my mobile is 599 77 66 55."


def transferred_payload(*, answered: bool = True) -> dict[str, Any]:
    """A call the agent put through to staff 35 s in; a person took it or not."""

    payload = post_call_payload()
    transcript: list[dict[str, Any]] = payload["data"]["transcript"]
    del transcript[1:]
    transcript.append(
        {
            "role": "agent",
            "message": "Connecting you to a colleague.",
            "time_in_call_secs": 35,
            "tool_calls": [{"tool_name": "transfer_to_number"}],
            "tool_results": [
                {
                    "tool_name": "transfer_to_number",
                    "result_value": "transferred" if answered else "no-answer",
                    "is_error": not answered,
                }
            ],
        }
    )
    # What the platform may still transcribe after a person took the call
    # (a conference keeps the agent on the line); a caller speaking again
    # would mean nobody took it.
    transcript.append(
        {
            "role": "agent",
            "message": STAFF_LINE if answered else "Nobody is free right now.",
            "time_in_call_secs": 50,
        }
    )
    payload["data"]["analysis"] = {"transcript_summary": "Giorgi took the call."}
    return payload


def only_call(setup: VoiceSetup) -> CallDocument:
    [call] = stored_calls(setup)
    return call


def test_without_settings_no_call_audio_is_kept() -> None:
    setup = build_voice_setup()

    process_call(setup, post_call_payload())

    call = only_call(setup)
    assert call.recording_declined is True
    assert call.recording_path is None
    assert setup.testbed.recording_storage.deleted == [PLATFORM_COPY]


def test_a_business_that_turned_recording_on_keeps_the_audio() -> None:
    setup = build_voice_setup()
    save_call_settings(setup, is_recording_enabled=True)

    process_call(setup, post_call_payload())

    call = only_call(setup)
    assert call.recording_declined is False
    assert str(call.recording_path) == PLATFORM_COPY
    assert setup.testbed.recording_storage.deleted == []


def test_the_staff_part_of_a_transferred_call_is_not_kept() -> None:
    setup = build_voice_setup()
    save_call_settings(setup, is_recording_enabled=True)

    process_call(setup, transferred_payload())

    call = only_call(setup)
    # The audio holds the staff member's conversation: it goes.
    assert call.recording_declined is True
    assert call.recording_path is None
    assert setup.testbed.recording_storage.deleted == [PLATFORM_COPY]
    transcript = str(call.transcript)
    assert "Giorgi" not in transcript and "599 77 66 55" not in transcript
    assert "AI ასისტენტი" in transcript
    assert call.analysis is None


def test_a_transfer_nobody_took_keeps_the_call_as_it_was() -> None:
    setup = build_voice_setup()
    save_call_settings(setup, is_recording_enabled=True)

    process_call(setup, transferred_payload(answered=False))

    call = only_call(setup)
    assert call.recording_declined is False
    assert str(call.recording_path) == PLATFORM_COPY
    assert "Nobody is free right now." in str(call.transcript)
