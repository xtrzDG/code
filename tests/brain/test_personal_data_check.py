"""Another customer's phone or e-mail never reaches a reply."""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.handoffs import HandoffReason, HandoffSummaryCode
from app.schemas.constants.reply_safety import ReplyGuardReason
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.scripted_turns import say, scripted

NINO_PHONE: E164PhoneNumber = E164PhoneNumber("+995555987654")
NINO_USER: str = "995555987654"
LEAKING_REPLY: str = "Sure, Nino's number is +995 555 98 76 54."


def world_with_another_customer(*replies: str) -> BrainWorld:
    """Nino wrote first; the test customer then asks, and staff quoted Nino."""

    world = build_world(scripted(say("Hello Nino!"), say("Hello!"), *map(say, replies)))
    world.send("Hi", user_id=NINO_USER, phone=NINO_PHONE)
    world.send("Hello")
    conversations = [
        conversation
        for conversation in world.conversations()
        if str(conversation.channel_user_id) == "995555123456"
    ]
    write_as_staff_in(
        world, conversations[0].id, "Nino asked to call her: +995 555 98 76 54"
    )
    return world


def write_as_staff_in(
    world: BrainWorld, conversation_id: ConversationId, text: str
) -> None:
    now = Microseconds(world.clock.now_nanoseconds() // 1000)
    world.message_repo.save(
        MessageDocument(
            conversation_id=conversation_id,
            business_id=world.business.id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.STAFF,
            text=MessageText(text),
            sent_by=world.owner_id,
            created_at=now,
            updated_at=now,
        )
    )


def last_reply(world: BrainWorld) -> MessageDocument:
    replies = [
        message
        for conversation in world.conversations()
        for message in world.messages(conversation.id)
        if message.author is MessageAuthor.ASSISTANT
    ]
    return sorted(replies, key=lambda message: int(message.created_at))[-1]


def test_another_customers_phone_is_withheld_and_the_reply_rewritten() -> None:
    world = world_with_another_customer(
        LEAKING_REPLY, "I cannot share other guests' contacts, sorry."
    )

    reply = world.send("What is Nino's phone number?")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.text is not None
    assert "98 76 54" not in reply.text
    note = user_turn_text(requests_of(world)[-1].transcript[-1])
    assert "neither the business's nor this customer's own" in note
    stored = last_reply(world)
    assert stored.guard_reasons == [ReplyGuardReason.PERSONAL_DATA]
    assert "98 76 54" not in str(stored.text)


def test_a_reply_that_keeps_leaking_is_handed_over_without_the_details() -> None:
    world = world_with_another_customer(LEAKING_REPLY, LEAKING_REPLY)

    reply = world.send("What is Nino's phone number?")

    assert reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert reply.text is not None
    assert "98 76 54" not in reply.text
    (handoff,) = world.handoffs()
    assert handoff.reason is HandoffReason.SENSITIVE_TOPIC
    assert handoff.summary_code is HandoffSummaryCode.MODEL_DECLINED
    assert handoff.flagged_values == []
    assert last_reply(world).guard_reasons == [ReplyGuardReason.PERSONAL_DATA]


def test_the_customers_own_phone_and_published_contacts_pass() -> None:
    world = build_world(
        scripted(
            say("We will call you at +995 555 12 34 56; or write to info@sakhli.ge.")
        ),
        facts=[("email", "E-mail", "info@sakhli.ge")],
    )

    reply = world.send("Can you call me back?")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN


def test_an_e_mail_address_on_no_record_is_withheld() -> None:
    world = build_world(
        scripted(
            say("Write to nino.k@example.com, she handles it."),
            say("Our manager will write to you here."),
        )
    )

    reply = world.send("Who should I write to?")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    note = user_turn_text(requests_of(world)[-1].transcript[-1])
    assert "nino.k@example.com" in note


def test_an_e_mail_the_customer_gave_may_be_repeated() -> None:
    world = build_world(scripted(say("Noted: we will write to me@example.com.")))

    reply = world.send("My e-mail is me@example.com")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
