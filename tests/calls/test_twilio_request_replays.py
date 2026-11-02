"""
Twilio's signature carries no time: a captured fallback or dial status
request would stay valid forever. Once its signature checks out, a request
(its address, call and status) is claimed for a day; a signed copy sent
again gets an empty <Response/> and changes nothing: no staff mobile rings,
no missed call, no text-back, no notice to the owner.
"""

from datetime import timedelta

import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.telephony.twilio_replay_guard import TwilioReplayGuard
from tests.calls.call_fallback_steps import (
    STAFF_MOBILE,
    dial_form,
    dial_path,
    fallback_form,
    fallback_path,
    fallback_settings,
    post_twilio,
    set_staff_mobile,
)
from tests.calls.call_steps import (
    add_staff_chat,
    connect_whatsapp,
    missed_calls,
    save_call_settings,
    staff_texts,
    whatsapp_templates,
)
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

EMPTY: str = '<?xml version="1.0" encoding="UTF-8"?><Response/>'
HANGUP: str = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
SECONDS_PER_HOUR: int = 3600


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup(settings=fallback_settings())
    save_call_settings(voice_setup)
    connect_whatsapp(voice_setup)
    add_staff_chat(voice_setup, language="en")
    return voice_setup


def test_a_replayed_fallback_rings_nobody_and_tells_nobody(setup: VoiceSetup) -> None:
    set_staff_mobile(setup)
    path = fallback_path(setup.business.id)

    first = post_twilio(setup, path, fallback_form())
    texts_after_first = len(staff_texts(setup))
    replay = post_twilio(setup, path, fallback_form())
    setup.testbed.clock.advance(23 * SECONDS_PER_HOUR)
    later_replay = post_twilio(setup, path, fallback_form())

    assert STAFF_MOBILE in first.text
    assert replay.status_code == 200
    assert replay.text == EMPTY
    assert later_replay.text == EMPTY
    assert len(staff_texts(setup)) == texts_after_first


def test_another_call_is_no_replay(setup: VoiceSetup) -> None:
    set_staff_mobile(setup)
    path = fallback_path(setup.business.id)

    post_twilio(setup, path, fallback_form())
    other = post_twilio(setup, path, fallback_form(call_sid="CA" + "7" * 32))

    assert STAFF_MOBILE in other.text


def test_a_replayed_dial_report_makes_no_second_missed_call(
    setup: VoiceSetup,
) -> None:
    path = dial_path(setup.business.id)

    first = post_twilio(setup, path, dial_form("busy"))
    replay = post_twilio(setup, path, dial_form("busy"))
    # Another status of the same call is its own report.
    other_status = post_twilio(setup, path, dial_form("no-answer"))

    assert first.text == HANGUP
    assert replay.text == EMPTY
    assert other_status.text == HANGUP
    assert len(missed_calls(setup)) == 1
    assert len(whatsapp_templates(setup)) == 1


def test_an_unsigned_request_claims_nothing(setup: VoiceSetup) -> None:
    set_staff_mobile(setup)
    path = fallback_path(setup.business.id)

    forged = post_twilio(setup, path, fallback_form(), signature="forged")
    genuine = post_twilio(setup, path, fallback_form())

    assert forged.status_code == 401
    assert STAFF_MOBILE in genuine.text


def test_a_claim_is_seen_for_at_least_a_day() -> None:
    guard = TwilioReplayGuard(InMemoryRateLimitBucketAdapter())
    start = Microseconds(1_790_000_000_000_000)

    def at(delta: timedelta) -> Microseconds:
        return Microseconds(int(start) + int(delta.total_seconds()) * 1_000_000)

    assert guard.is_replay("claim", start) is False
    assert guard.is_replay("claim", at(timedelta(hours=1))) is True
    assert guard.is_replay("claim", at(timedelta(hours=24))) is True
    assert guard.is_replay("other", at(timedelta(hours=1))) is False
    assert guard.is_replay("claim", at(timedelta(hours=49))) is False
