"""
The call fallback never rings a staff phone the call would loop through:
the phone the call came from, was forwarded from, or the rented line
itself (an owner who entered "our phone" as the handoff phone). The owner
is told that phone was skipped, not that there was none.
"""

import pytest

from app.schemas.constants.calls import MissedCallReason
from tests.calls.call_fallback_steps import (
    STAFF_MOBILE,
    fallback_settings,
    set_staff_mobile,
)
from tests.calls.call_steps import (
    add_staff_chat,
    connect_whatsapp,
    missed_calls,
    save_call_settings,
    whatsapp_templates,
)
from tests.calls.test_call_fallback import HANGUP, call_falls_back, notices
from tests.channels.voice_setup import (
    ASSISTANT_LINE,
    CALLER,
    VoiceSetup,
    build_voice_setup,
)

NO_PHONE_HINT: str = "Add a phone for calls that need a person"
LOOP_HINT: str = "was not rung, because the call came from it"


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup(settings=fallback_settings())
    save_call_settings(voice_setup)
    connect_whatsapp(voice_setup)
    add_staff_chat(voice_setup, language="en")
    return voice_setup


def test_a_staff_phone_that_is_the_line_itself_is_never_dialled(
    setup: VoiceSetup,
) -> None:
    set_staff_mobile(setup, ASSISTANT_LINE)

    response = call_falls_back(setup)

    assert response.text == HANGUP
    [missed] = missed_calls(setup)
    assert missed.reason is MissedCallReason.NOT_STARTED
    assert len(whatsapp_templates(setup)) == 1
    [notice] = notices(setup)
    assert LOOP_HINT in notice
    assert NO_PHONE_HINT not in notice


@pytest.mark.parametrize(
    ("caller", "forwarded_from"),
    [(STAFF_MOBILE, None), (CALLER, "555 12 34 56")],
)
def test_the_owner_hears_which_phone_was_skipped(
    setup: VoiceSetup, caller: str, forwarded_from: str | None
) -> None:
    set_staff_mobile(setup)
    form: dict[str, str] = {"caller": caller}
    if forwarded_from is not None:
        form["forwarded_from"] = forwarded_from

    call_falls_back(setup, **form)

    [notice] = notices(setup)
    assert LOOP_HINT in notice
    assert "555 12 34 56" in notice
    assert NO_PHONE_HINT not in notice


def test_without_a_staff_phone_the_owner_is_asked_to_add_one(
    setup: VoiceSetup,
) -> None:
    call_falls_back(setup)

    [notice] = notices(setup)
    assert NO_PHONE_HINT in notice
    assert LOOP_HINT not in notice
