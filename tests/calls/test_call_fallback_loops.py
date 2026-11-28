"""
The call fallback never rings a staff phone the call would loop through:
the phone the call came from, was forwarded from, or the rented line
itself (an owner who entered "our phone" as the handoff phone), nor for a
call from the line itself (the staff phone forwarding the call put through
to it back to the line, its carrier not saying so). That call is rejected
unanswered, so the caller of the call put through is the missed call, not
the line, even when staff blocked a contact holding the line's number.
The owner is told that phone was skipped, not that there was none.
"""

import pytest

from app.schemas.constants.calls import MissedCallReason, TextBackStatus
from app.schemas.constants.channels import ChannelKind
from tests.calls.call_fallback_steps import (
    CALL_SID,
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
from tests.calls.test_blocked_callers_by_number import holder, identity
from tests.calls.test_call_fallback import (
    HANGUP,
    call_falls_back,
    dial_ends,
    dial_twiml,
    notices,
)
from tests.channels.voice_setup import (
    ASSISTANT_LINE,
    CALLER,
    VoiceSetup,
    build_voice_setup,
)

NO_PHONE_HINT: str = "Add a phone for calls that need a person"
LOOP_HINT: str = "was not rung, because the call came from it"
REJECT_AS_BUSY: str = (
    '<?xml version="1.0" encoding="UTF-8"?><Response><Reject reason="busy"/></Response>'
)
# The call put through to the staff phone, forwarded back to the line.
LOOPED_CALL_SID: str = "CA" + "0" * 31 + "7"


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


def test_a_call_from_the_line_itself_is_rejected_unanswered(
    setup: VoiceSetup,
) -> None:
    # The staff phone shows the line as the caller id of the call put
    # through to it; forwarded back unanswered, that call comes "from" the
    # line, and not every carrier adds ForwardedFrom. Answering it, even to
    # hang up, would complete the call put through.
    set_staff_mobile(setup)

    response = call_falls_back(setup, caller=ASSISTANT_LINE, call_sid=LOOPED_CALL_SID)

    assert response.text == REJECT_AS_BUSY
    # Its caller is the platform's own line: no missed call, no text-back.
    assert missed_calls(setup) == []
    assert whatsapp_templates(setup) == []
    [notice] = notices(setup)
    assert LOOP_HINT in notice
    assert "555 12 34 56" in notice
    assert NO_PHONE_HINT not in notice


@pytest.mark.parametrize("is_line_number_blocked", [False, True])
def test_the_caller_whose_call_came_back_is_the_missed_call(
    setup: VoiceSetup, is_line_number_blocked: bool
) -> None:
    set_staff_mobile(setup)
    if is_line_number_blocked:
        # The call-only contact of a call that spoofed the line's own number
        # (the agent took it), blocked by staff: it blocks no person.
        holder(
            setup,
            [identity(ChannelKind.PHONE, ASSISTANT_LINE)],
            is_blocked=True,
            phone_number=ASSISTANT_LINE,
        )

    put_through = call_falls_back(setup)
    came_back = call_falls_back(setup, caller=ASSISTANT_LINE, call_sid=LOOPED_CALL_SID)
    # The staff phone's forwarding failed, so the call to it ends as busy.
    dial_ends(setup, "busy")

    assert put_through.text == dial_twiml(setup.business.id, STAFF_MOBILE)
    assert came_back.text == REJECT_AS_BUSY
    [missed] = missed_calls(setup)
    assert str(missed.provider_call_id) == CALL_SID
    assert str(missed.caller_phone_number) == CALLER
    assert missed.reason is MissedCallReason.BUSY
    assert missed.status is TextBackStatus.SENT
    assert [template["to"] for template in whatsapp_templates(setup)] == [
        CALLER.removeprefix("+")
    ]


def test_without_a_staff_phone_the_owner_is_asked_to_add_one(
    setup: VoiceSetup,
) -> None:
    call_falls_back(setup)

    [notice] = notices(setup)
    assert NO_PHONE_HINT in notice
    assert LOOP_HINT not in notice
