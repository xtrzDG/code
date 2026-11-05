"""
The voice agent never promises a text it cannot send. A caller id reaches
no messenger contact (a call has a call-only contact of its own), so after
a call nobody is texted a link or a confirmation because of the number,
and send_link says so (texted_after_call false) whoever holds the number:
a customer writing today on WhatsApp or Telegram, the WhatsApp contact of
a text-back, or an older contact holding both the number and a messenger.
"""

from collections.abc import Callable

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.channels.caller_reachability import list_reachable_identities
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import say, scripted
from tests.brain.test_voice_caller_contacts import call_contact
from tests.brain.test_voice_tool_calls import voice_call

CALLER: str = "+995599123456"
WHATSAPP_ID: str = CALLER.removeprefix("+")


def connect(world: BrainWorld, kind: ChannelKind, external_id: str) -> None:
    world.channel_repo.save(
        ChannelDocument(
            business_id=world.business.id,
            kind=kind,
            external_id=ChannelExternalId(external_id),
            status=ChannelStatus.CONNECTED,
        )
    )


def nobody(world: BrainWorld) -> None:
    """A number the business has never seen."""


def whatsapp_customer_writing_today(world: BrainWorld) -> None:
    world.send("Ciao", channel=ChannelKind.WHATSAPP, user_id=WHATSAPP_ID, phone=None)


def telegram_customer_who_proved_it(world: BrainWorld) -> None:
    world.send(
        "Ciao",
        channel=ChannelKind.TELEGRAM,
        user_id="555000111",
        phone=E164PhoneNumber(CALLER),
    )


def text_back_contact(world: BrainWorld) -> None:
    holder(world, [identity(ChannelKind.WHATSAPP, WHATSAPP_ID)])


def older_contact_with_both(world: BrainWorld) -> None:
    holder(
        world,
        [identity(ChannelKind.PHONE, CALLER), identity(ChannelKind.TELEGRAM, "555")],
    )


def identity(channel: ChannelKind, user_id: str) -> ChannelIdentity:
    return ChannelIdentity(channel=channel, channel_user_id=ChannelUserId(user_id))


def holder(world: BrainWorld, identities: list[ChannelIdentity]) -> None:
    world.contact_repo.save(
        ContactDocument(
            business_id=world.business.id,
            phone_number=E164PhoneNumber(CALLER),
            channel_identities=identities,
        )
    )


@pytest.mark.parametrize(
    "known_as",
    [
        nobody,
        whatsapp_customer_writing_today,
        telegram_customer_who_proved_it,
        text_back_contact,
        older_contact_with_both,
    ],
)
def test_a_caller_is_never_promised_a_text(
    known_as: Callable[[BrainWorld], None],
) -> None:
    world = build_world(scripted(say("Ciao!")))
    connect(world, ChannelKind.TELEGRAM, "sakhli_bot")
    connect(world, ChannelKind.WHATSAPP, "wa_number_1")
    known_as(world)

    result, is_error = voice_call(
        world, AssistantToolName.SEND_LINK, '{"kind":"menu"}', caller=CALLER
    )

    assert is_error is False
    assert result["texted_after_call"] is False
    assert "url" not in result
    assert "do not promise one" in str(result["note"])
    # After the call the outbox looks for the same messengers: none.
    caller = call_contact(world, "el_call_1")
    assert (
        list_reachable_identities(world.channel_repo, world.business.id, caller) == []
    )
