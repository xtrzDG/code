"""
A number staff blocked is refused by the voice agent at call start, and the
line's fallback does not put it through to the staff mobile instead: the
call ends, with no missed call, no text-back and no notice to the owner.
"""

from app.schemas.domain.contacts import ContactBlock, ContactDocument
from app.schemas.typings.users.prefixed_id import UserId
from tests.calls.call_fallback_steps import (
    STAFF_MOBILE,
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
)
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

HANGUP: str = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
OTHER_CALLER: str = "+995599654321"


def blocked_caller_setup() -> VoiceSetup:
    """The caller (the setup's contact, by their phone) is blocked by staff."""

    setup = build_voice_setup(settings=fallback_settings())
    save_call_settings(setup, is_text_back_enabled=True)
    connect_whatsapp(setup)
    add_staff_chat(setup, language="en")
    set_staff_mobile(setup)
    block = ContactBlock(
        blocked_at=setup.testbed.clock.now_microseconds(), blocked_by=UserId()
    )

    def blocked_by_staff(contact: ContactDocument) -> None:
        contact.block = block

    setup.testbed.contact_repo.change_card(
        setup.business.id, setup.contact.id, blocked_by_staff
    )
    return setup


def test_a_blocked_caller_is_not_put_through_to_staff() -> None:
    setup = blocked_caller_setup()

    response = post_twilio(setup, fallback_path(setup.business.id), fallback_form())

    assert response.status_code == 200, response.text
    assert response.text == HANGUP
    assert STAFF_MOBILE not in response.text
    assert missed_calls(setup) == []
    assert staff_texts(setup) == []


def test_another_caller_still_reaches_the_staff_mobile() -> None:
    setup = blocked_caller_setup()

    response = post_twilio(
        setup,
        fallback_path(setup.business.id),
        fallback_form(caller=OTHER_CALLER),
    )

    assert response.status_code == 200, response.text
    assert f"<Number>{STAFF_MOBILE}</Number>" in response.text
