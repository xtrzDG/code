"""Who the engine talks to: contact identities, proven phones and sandbox isolation."""

import json

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.bookings import CancelBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
)
from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import call_tool, say, scripted


def test_contact_and_channel_identity_are_reused_and_completed() -> None:
    world = build_world(scripted(say("Привет!"), say("Да."), say("Конечно.")))

    world.send("Привет", phone=None)
    world.send("Есть парковка?", name="Георгий", phone=None)
    world.send("Здравствуйте", channel=ChannelKind.TELEGRAM, user_id="42", phone=None)

    contacts = world.contacts()
    assert len(contacts) == 2
    whatsapp_contact = next(
        contact
        for contact in contacts
        if contact.channel_identities[0].channel is ChannelKind.WHATSAPP
    )
    assert whatsapp_contact.name == "Георгий"
    assert len(world.conversations()) == 2


def test_phone_number_links_a_new_channel_to_the_known_contact() -> None:
    world = build_world(scripted(say("Hello!"), say("Hi again!")))

    world.send("Hi", channel=ChannelKind.WHATSAPP, user_id="995555123456")
    world.send("Hi", channel=ChannelKind.TELEGRAM, user_id="777")

    contacts = world.contacts()
    assert len(contacts) == 1
    assert {identity.channel for identity in contacts[0].channel_identities} == {
        ChannelKind.WHATSAPP,
        ChannelKind.TELEGRAM,
    }


def test_sandbox_messages_are_isolated_and_work_before_launch() -> None:
    world = build_world(scripted(say("Test reply"), say("Real reply")))
    world.business.status = BusinessStatus.TESTING
    world.save_business(world.business)

    sandbox = world.send("Test booking", is_sandbox=True)
    with pytest.raises(ConflictError, match="not live"):
        world.send("Real customer")

    world.business.status = BusinessStatus.LIVE
    world.save_business(world.business)
    real = world.send("Real customer")

    conversations = {
        conversation.id: conversation for conversation in world.conversations()
    }
    assert conversations[sandbox.conversation_id].is_sandbox is True
    assert conversations[real.conversation_id].is_sandbox is False
    assert sandbox.conversation_id != real.conversation_id
    assert [event.kind for event in world.usage_events()] == [UsageKind.DIALOG]


def test_sandbox_messages_never_match_real_contacts_by_phone() -> None:
    world = build_world(scripted(say("Real"), say("Sandbox")))

    world.send("Hello", user_id="995555123456")
    world.send("Hello", is_sandbox=True, user_id="autotest-1")

    assert len(world.contacts()) == 2


def test_only_a_phone_the_channel_proved_reaches_bookings_by_phone() -> None:
    victim_phone = E164PhoneNumber("+995599765432")
    cancel_by_date = call_tool(
        AssistantToolName.CANCEL_BOOKING,
        json.dumps({"booking_id": None, "phone": None, "date": "2026-10-06"}),
    )
    world = build_world(
        scripted(
            cancel_by_date,
            say("Sorry, I could not find it."),
            cancel_by_date,
            say("Your booking is cancelled."),
        )
    )
    typed_contact = ContactDocument(
        business_id=world.business.id,
        name=ContactName("Typed by someone"),
        phone_number=victim_phone,
    )
    world.contact_repo.save(typed_contact)

    world.send(
        "Cancel my booking for 6 October",
        channel=ChannelKind.TELEGRAM,
        user_id="777",
        phone=None,
    )
    world.send(
        "Cancel my booking for 6 October", user_id="995599765432", phone=victim_phone
    )

    stranger_command, owner_command = [
        command
        for command in world.bookings.commands
        if isinstance(command, CancelBookingCommand)
    ]
    assert stranger_command.contact_phone_number is None
    assert owner_command.contact_phone_number == victim_phone
    whatsapp_contact = next(
        contact
        for contact in world.contacts()
        if any(
            identity.channel is ChannelKind.WHATSAPP
            for identity in contact.channel_identities
        )
    )
    # A typed phone proves nothing, so the WhatsApp sender is not merged
    # into the contact that only typed that number.
    assert whatsapp_contact.id != typed_contact.id
    assert whatsapp_contact.verified_phone_number == victim_phone
    stored_typed = world.contact_repo.get(world.business.id, typed_contact.id)
    assert stored_typed is not None
    assert stored_typed.verified_phone_number is None
