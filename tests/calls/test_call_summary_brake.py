"""
While a platform brake holds (a platform admin's pause, the daily budget
stop) a finished call asks no model: staff still get its report, without
a summary, and the call keeps none (as when the model is unavailable).
"""

import json

import pytest

from app.schemas.constants.spend import PlatformBrake
from tests.calls.call_steps import add_staff_chat, save_call_settings, staff_texts
from tests.channels.post_call_steps import post_call_payload, process_call, stored_calls
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

SUMMARIES: str = json.dumps(
    {"ka": "სტუმარს ოთხი ადგილი სურს.", "it": "L'ospite vuole un tavolo."},
    ensure_ascii=False,
)


def braked_setup(brake: PlatformBrake) -> VoiceSetup:
    setup = build_voice_setup()
    add_staff_chat(setup, language="it")
    setup.testbed.summary_answers.append(SUMMARIES)
    setup.testbed.platform_brakes.brake = brake
    return setup


@pytest.mark.parametrize("brake", list(PlatformBrake))
def test_no_model_is_asked_and_staff_still_hear(brake: PlatformBrake) -> None:
    setup = braked_setup(brake)

    process_call(setup, post_call_payload())

    assert setup.testbed.summary_requests == []
    [call] = stored_calls(setup)
    assert call.summarized_at is None
    assert call.summaries == []
    [text] = staff_texts(setup)
    lines = str(text.text).split("\n")
    assert lines[0] == "Riepilogo della chiamata · Funicular VR"
    assert lines[2] == "Esito: informazioni fornite"
    assert setup.testbed.platform_brakes.readings != []


def test_the_next_call_after_the_brake_is_summarized() -> None:
    setup = braked_setup(PlatformBrake.PAUSED)
    process_call(setup, post_call_payload("conv_braked"))
    setup.testbed.platform_brakes.brake = None

    process_call(setup, post_call_payload("conv_after"))

    [request] = setup.testbed.summary_requests
    assert "Languages: ka, it" in str(request.transcript)
    calls = {str(call.provider_call_id): call for call in stored_calls(setup)}
    assert calls["conv_braked"].summaries == []
    assert {str(summary.text) for summary in calls["conv_after"].summaries} == {
        "სტუმარს ოთხი ადგილი სურს.",
        "L'ospite vuole un tavolo.",
    }
    assert len(staff_texts(setup)) == 2


def test_summaries_off_ask_no_model_for_the_memory_either() -> None:
    setup = braked_setup(PlatformBrake.BUDGET_STOP)
    save_call_settings(setup, is_summary_enabled=False, is_text_back_enabled=False)

    process_call(setup, post_call_payload())

    assert setup.testbed.summary_requests == []
    assert staff_texts(setup) == []
    [call] = stored_calls(setup)
    assert call.summarized_at is None
