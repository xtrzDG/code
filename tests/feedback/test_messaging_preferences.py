"""
STOP and START, answered by the platform before the assistant: STOP (or its
translation, as the whole message) records the opt-out on the contact,
audited, and confirms it; START lifts it; elsewhere the words are ordinary
messages the assistant answers.
"""

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.contacts import ContactDocument
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import say, scripted


def only_contact(world: BrainWorld) -> ContactDocument:
    [contact] = world.contacts()
    return contact


def opt_out_audit(world: BrainWorld) -> list[AuditAction]:
    return [
        entry.action
        for entry in world.audit_log_repo.list_by_business(world.business.id)
        if str(entry.entity) == "message_opt_out"
    ]


@pytest.mark.parametrize("stop", ["STOP", "stop.", "Стоп", "სტოპ", "Unsubscribe"])
def test_stop_records_the_opt_out_and_confirms_it(stop: str) -> None:
    world = build_world(scripted())

    reply = world.send(stop)

    assert only_contact(world).opted_out_channels == [ChannelKind.WHATSAPP]
    assert reply.text is not None
    assert "Sakhli" in str(reply.text)
    assert opt_out_audit(world) == [AuditAction.CREATE]
    assert world.turns(reply.conversation_id) == []


def test_stop_in_english_is_confirmed_in_english() -> None:
    world = build_world(scripted())

    reply = world.send("STOP", channel=ChannelKind.TELEGRAM, user_id="555000111")

    assert "Done: Sakhli will no longer send you" in str(reply.text)
    assert only_contact(world).opted_out_channels == [ChannelKind.TELEGRAM]


def test_a_second_stop_is_confirmed_without_a_second_record() -> None:
    world = build_world(scripted())
    world.send("STOP")

    reply = world.send("STOP")

    assert reply.text is not None
    assert only_contact(world).opted_out_channels == [ChannelKind.WHATSAPP]
    assert opt_out_audit(world) == [AuditAction.CREATE]


def test_start_lifts_every_opt_out() -> None:
    world = build_world(scripted())
    world.send("STOP")
    world.send("STOP", channel=ChannelKind.TELEGRAM, user_id="555000111")

    reply = world.send("START")

    assert only_contact(world).opted_out_channels == []
    assert "Welcome back! Sakhli will send you" in str(reply.text)
    assert opt_out_audit(world) == [
        AuditAction.CREATE,
        AuditAction.CREATE,
        AuditAction.DELETE,
    ]


def test_start_from_a_customer_who_never_stopped_is_for_the_assistant() -> None:
    world = build_world(scripted(say("Hello! Shall I book a table?")))

    reply = world.send("Start")

    assert str(reply.text).endswith("Hello! Shall I book a table?")
    assert opt_out_audit(world) == []


def test_stop_inside_a_sentence_is_for_the_assistant() -> None:
    world = build_world(scripted(say("The bus stop is right outside.")))

    reply = world.send("Where is the nearest bus stop?")

    assert str(reply.text).endswith("The bus stop is right outside.")
    assert only_contact(world).opted_out_channels == []


def test_the_owners_test_chat_has_no_opt_out() -> None:
    world = build_world(scripted(say("This is the test chat.")))

    reply = world.send("STOP", is_sandbox=True)

    assert str(reply.text).endswith("This is the test chat.")
    assert opt_out_audit(world) == []


def test_a_web_chat_stop_is_for_the_assistant() -> None:
    world = build_world(scripted(say("How can I help?")))

    reply = world.send("STOP", channel=ChannelKind.WEB_CHAT, phone=None)

    assert str(reply.text).endswith("How can I help?")
    assert opt_out_audit(world) == []
