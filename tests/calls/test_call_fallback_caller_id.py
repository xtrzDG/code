"""
A call the platform puts through to staff presents only the platform's own
line (the rented number that was called) as its caller id, never the
caller's number: no impersonation through the platform, and no Italian
caller id the carriers' anti-spoofing filters would drop. A fallback that
names no line puts nobody through.
"""

import re

import pytest

from app.schemas.constants.calls import MissedCallReason
from tests.calls.call_fallback_steps import (
    STAFF_MOBILE,
    fallback_form,
    fallback_path,
    fallback_settings,
    post_twilio,
    set_staff_mobile,
)
from tests.calls.call_steps import missed_calls, save_call_settings
from tests.channels.voice_setup import (
    ASSISTANT_LINE,
    CALLER,
    VoiceSetup,
    build_voice_setup,
)

CALLER_ID: re.Pattern[str] = re.compile(r'callerId="([^"]*)"')


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup(settings=fallback_settings())
    save_call_settings(voice_setup)
    set_staff_mobile(voice_setup)
    return voice_setup


def test_the_staff_mobile_sees_the_line_not_the_caller(setup: VoiceSetup) -> None:
    response = post_twilio(
        setup, fallback_path(setup.business.id), fallback_form(caller=CALLER)
    )

    assert f"<Number>{STAFF_MOBILE}</Number>" in response.text
    assert CALLER_ID.findall(response.text) == [ASSISTANT_LINE]
    assert CALLER not in response.text


def test_a_line_in_a_national_format_is_presented_in_e164(setup: VoiceSetup) -> None:
    response = post_twilio(
        setup,
        fallback_path(setup.business.id),
        fallback_form(called="32 2 00 00 00"),
    )

    assert CALLER_ID.findall(response.text) == [ASSISTANT_LINE]


def test_without_a_line_to_present_nobody_is_put_through(setup: VoiceSetup) -> None:
    response = post_twilio(
        setup, fallback_path(setup.business.id), fallback_form(called="")
    )

    assert "<Dial" not in response.text
    assert "<Hangup/>" in response.text
    [missed] = missed_calls(setup)
    assert missed.reason is MissedCallReason.NOT_STARTED
