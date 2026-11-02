"""
Several contacts may hold one number (a call never joins a contact a
channel proved): a proved customer, the call-only contact of earlier
calls, a contact of a single call, the WhatsApp customer of a text-back.
One blocked among them refuses the number, at call start and on the
line's fallback to the staff mobile, whichever field holds it (one of
several proved phones, a WhatsApp account alone); another number still
gets through.
"""

from collections.abc import Callable

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ChannelIdentity, ContactBlock, ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from tests.calls.call_fallback_steps import (
    STAFF_MOBILE,
    fallback_form,
    fallback_path,
    fallback_settings,
    post_twilio,
    set_staff_mobile,
)
from tests.calls.call_steps import connect_whatsapp, save_call_settings
from tests.channels.test_voice_webhooks import post_start
from tests.channels.voice_setup import CALLER, VoiceSetup, build_voice_setup

HANGUP: str = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
OTHER_CALLER: str = "+995599654321"
# A customer's given phone that is not the calling number.
GIVEN_ELSEWHERE: str = "+995599111222"


def identity(channel: ChannelKind, user_id: str) -> ChannelIdentity:
    return ChannelIdentity(channel=channel, channel_user_id=ChannelUserId(user_id))


def holder(
    setup: VoiceSetup,
    identities: list[ChannelIdentity],
    business_id: BusinessId | None = None,
    is_blocked: bool = False,
    phone_number: str | None = CALLER,
    verified_phone_number: str | None = None,
) -> ContactDocument:
    """A contact holding the caller's number (by default kept to call back)."""

    now = setup.testbed.clock.now_microseconds()
    contact = ContactDocument(
        business_id=business_id or setup.business.id,
        phone_number=None if phone_number is None else E164PhoneNumber(phone_number),
        verified_phone_number=(
            None
            if verified_phone_number is None
            else E164PhoneNumber(verified_phone_number)
        ),
        channel_identities=identities,
        block=ContactBlock(blocked_at=now, blocked_by=UserId()) if is_blocked else None,
        created_at=now,
        updated_at=now,
    )
    setup.testbed.contact_repo.save(contact)
    return contact


def single_call_blocked(setup: VoiceSetup) -> None:
    """
    The setup's contact proved the number (and holds its PHONE identity
    from an older call); staff blocked a contact of a single call.
    """

    setup.contact.verified_phone_number = E164PhoneNumber(CALLER)
    setup.testbed.contact_repo.save(setup.contact)
    holder(setup, [identity(ChannelKind.PHONE, "el_call_7")], is_blocked=True)


def text_back_contact_blocked(setup: VoiceSetup) -> None:
    """
    The setup's contact is the call-only contact of the number; staff
    blocked the WhatsApp customer a text-back wrote to.
    """

    setup.contact.channel_identities = [identity(ChannelKind.PHONE, CALLER)]
    setup.testbed.contact_repo.save(setup.contact)
    holder(
        setup,
        [identity(ChannelKind.WHATSAPP, CALLER.removeprefix("+"))],
        is_blocked=True,
    )


def second_prover_blocked(setup: VoiceSetup) -> None:
    """
    Two customers proved the number (each keeps another given phone);
    staff blocked the one who proved it later.
    """

    for user_id, is_blocked in (("556", False), ("557", True)):
        holder(
            setup,
            [identity(ChannelKind.TELEGRAM, user_id)],
            is_blocked=is_blocked,
            phone_number=GIVEN_ELSEWHERE,
            verified_phone_number=CALLER,
        )


def whatsapp_account_blocked(setup: VoiceSetup) -> None:
    """
    The setup's contact is the call-only contact of the number; staff
    blocked the number's WhatsApp customer, who keeps no phone of their
    own (it was removed from the card).
    """

    setup.contact.channel_identities = [identity(ChannelKind.PHONE, CALLER)]
    setup.testbed.contact_repo.save(setup.contact)
    holder(
        setup,
        [identity(ChannelKind.WHATSAPP, CALLER.removeprefix("+"))],
        is_blocked=True,
        phone_number=None,
    )


SCENARIOS = pytest.mark.parametrize(
    "blocked_holder",
    [
        single_call_blocked,
        text_back_contact_blocked,
        second_prover_blocked,
        whatsapp_account_blocked,
    ],
)


@SCENARIOS
def test_the_voice_agent_refuses_the_number(
    blocked_holder: Callable[[VoiceSetup], None],
) -> None:
    setup = build_voice_setup()
    blocked_holder(setup)

    blocked = post_start(setup)
    other = post_start(setup, caller=OTHER_CALLER)

    assert blocked.status_code == 409, blocked.text
    assert "blocked" in blocked.text
    assert other.status_code == 200, other.text


@SCENARIOS
def test_the_fallback_does_not_ring_the_staff_mobile(
    blocked_holder: Callable[[VoiceSetup], None],
) -> None:
    setup = build_voice_setup(settings=fallback_settings())
    save_call_settings(setup, is_text_back_enabled=True)
    connect_whatsapp(setup)
    set_staff_mobile(setup)
    blocked_holder(setup)

    blocked = post_twilio(setup, fallback_path(setup.business.id), fallback_form())
    other = post_twilio(
        setup,
        fallback_path(setup.business.id),
        fallback_form(caller=OTHER_CALLER, call_sid="CA" + "0" * 31 + "3"),
    )

    assert blocked.status_code == 200, blocked.text
    assert blocked.text == HANGUP
    assert f"<Number>{STAFF_MOBILE}</Number>" in other.text


def test_every_contact_holding_a_number_is_listed() -> None:
    setup = build_voice_setup()
    single_call = holder(setup, [identity(ChannelKind.PHONE, "el_call_7")])
    holder(setup, [identity(ChannelKind.PHONE, "el_call_8")], business_id=BusinessId())
    provers = [
        holder(
            setup,
            [identity(ChannelKind.TELEGRAM, user_id)],
            phone_number=GIVEN_ELSEWHERE,
            verified_phone_number=CALLER,
        )
        for user_id in ("556", "557")
    ]
    repo = setup.testbed.contact_repo
    caller = E164PhoneNumber(CALLER)

    holders = repo.list_by_phone_number(setup.business.id, caller)
    proved = repo.list_by_verified_phone_number(setup.business.id, caller)
    nobody = [
        *repo.list_by_phone_number(setup.business.id, E164PhoneNumber(OTHER_CALLER)),
        *repo.list_by_verified_phone_number(
            setup.business.id, E164PhoneNumber(OTHER_CALLER)
        ),
    ]

    assert sorted(str(contact.id) for contact in holders) == sorted(
        [str(setup.contact.id), str(single_call.id)]
    )
    assert sorted(str(contact.id) for contact in proved) == sorted(
        str(contact.id) for contact in provers
    )
    assert nobody == []
