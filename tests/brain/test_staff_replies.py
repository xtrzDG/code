"""Staff replies from the cabinet over the customer's channel."""

from datetime import timedelta

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.conversations.prefixed_id import ConversationId
from tests.brain.brain_world import build_world
from tests.brain.conversation_cabinet_helpers import DAY_MICROSECONDS, Cabinet
from tests.brain.scripted_turns import say, scripted


class TestStaffReplies:
    def test_telegram_reply_is_sent_stored_audited_and_not_answered(self) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send(
            "Hi", channel=ChannelKind.TELEGRAM, user_id="tg-7", phone=None
        )
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.TELEGRAM)
        assert cabinet.card(reply.conversation_id)["reply"] == {
            "is_available": True,
            "block": None,
            "delivery": "sent",
            "window_closes_at": None,
            "template": None,
        }
        world.clock.advance(timedelta(minutes=5))

        sent = cabinet.reply(reply.conversation_id, "  We saved table 4 for you.  ")

        assert sent.status_code == 201, sent.text
        assert sent.json()["delivery"] == "sent"
        message = sent.json()["message"]
        assert message["author"] == "staff"
        assert message["direction"] == "outbound"
        assert message["text"] == "We saved table 4 for you."
        assert message["sent_by"] == str(world.staff_id)
        assert cabinet.storage.outbox.sent == [
            (ChannelKind.TELEGRAM, "tg-7", "We saved table 4 for you.")
        ]
        stored = world.messages(reply.conversation_id)
        assert [item.author for item in stored] == [
            MessageAuthor.CUSTOMER,
            MessageAuthor.ASSISTANT,
            MessageAuthor.STAFF,
        ]
        assert stored[-1].sent_by == world.staff_id
        conversation: ConversationDocument = world.conversations()[0]
        assert conversation.last_message_at == stored[-1].created_at
        audit = world.audit_log_repo.list_by_business(world.business.id)
        assert (audit[-1].action, audit[-1].entity, audit[-1].actor_id) == (
            AuditAction.CREATE,
            "message",
            world.staff_id,
        )
        assert audit[-1].entity_id == message["id"]
        assert audit[-1].ip_address == "testclient"
        assert len(world.turns(reply.conversation_id)) == 2

    def test_whatsapp_reply_only_within_24_hours_of_the_customer(self) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send("Hi")
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WHATSAPP)
        world.clock.advance(timedelta(hours=23))

        state = cabinet.card(reply.conversation_id)["reply"]
        sent = cabinet.reply(reply.conversation_id, "Still there?")
        world.clock.advance(timedelta(hours=2))
        closed_state = cabinet.card(reply.conversation_id)["reply"]
        refused = cabinet.reply(reply.conversation_id, "Hello again")

        customer_wrote_at = int(world.messages(reply.conversation_id)[0].created_at)
        assert state["is_available"] is True
        assert state["window_closes_at"] == customer_wrote_at + DAY_MICROSECONDS
        assert sent.status_code == 201
        assert closed_state["is_available"] is False
        assert closed_state["block"] == "window_closed"
        assert refused.status_code == 409
        assert "24 hours" in refused.json()["message"]
        assert len(cabinet.storage.outbox.sent) == 1

    def test_website_chat_keeps_the_message_for_the_widget(self) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send(
            "Hi", channel=ChannelKind.WEB_CHAT, user_id="visitor-1", phone=None
        )
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WEB_CHAT)

        sent = cabinet.reply(reply.conversation_id, "A manager here.", token="owner")

        assert sent.status_code == 201
        assert sent.json()["delivery"] == "stored_for_widget"
        assert cabinet.storage.outbox.sent == []
        assert world.messages(reply.conversation_id)[-1].text == "A manager here."

    def test_calls_tests_and_disconnected_channels_are_refused(self) -> None:
        world = build_world(scripted(say("a"), say("b"), say("c")))
        call = world.send("Hi", channel=ChannelKind.PHONE)
        test = world.send("Hi", is_sandbox=True, user_id="autotest", phone=None)
        telegram = world.send(
            "Hi", channel=ChannelKind.TELEGRAM, user_id="tg-1", phone=None
        )
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.TELEGRAM, ChannelStatus.DISABLED)

        blocks = {
            name: cabinet.card(conversation_id)["reply"]["block"]
            for name, conversation_id in (
                ("call", call.conversation_id),
                ("test", test.conversation_id),
                ("telegram", telegram.conversation_id),
            )
        }
        responses = [
            cabinet.reply(conversation_id, "Hello")
            for conversation_id in (
                call.conversation_id,
                test.conversation_id,
                telegram.conversation_id,
            )
        ]

        assert blocks == {
            "call": "voice_call",
            "test": "test_conversation",
            "telegram": "channel_disconnected",
        }
        assert [response.status_code for response in responses] == [409, 409, 409]
        assert "call the customer back" in responses[0].json()["message"]
        assert cabinet.storage.outbox.sent == []

    def test_a_channel_in_error_still_takes_staff_replies(self) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send(
            "Hi", channel=ChannelKind.TELEGRAM, user_id="tg-9", phone=None
        )
        cabinet = Cabinet(world)
        # The platform refused the token once; the next delivery may heal it.
        cabinet.connect(ChannelKind.TELEGRAM, ChannelStatus.ERROR)

        state = cabinet.card(reply.conversation_id)["reply"]
        sent = cabinet.reply(reply.conversation_id, "We are on it.")

        assert state["is_available"] is True
        assert state["delivery"] == "sent"
        assert sent.status_code == 201, sent.text
        assert cabinet.storage.outbox.sent == [
            (ChannelKind.TELEGRAM, "tg-9", "We are on it.")
        ]

    def test_a_reply_is_queued_with_its_delivery_state_and_bad_input_refused(
        self,
    ) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send(
            "Hi", channel=ChannelKind.TELEGRAM, user_id="tg-7", phone=None
        )
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.TELEGRAM)

        queued = cabinet.reply(reply.conversation_id, "Hello")
        empty = cabinet.reply(reply.conversation_id, "   ")
        long = cabinet.reply(reply.conversation_id, "x" * 4001)
        stranger = cabinet.reply(reply.conversation_id, "Hi", token="stranger")
        unknown = cabinet.reply(ConversationId(), "Hi")

        # Stored and queued at once; the worker sends it with retries.
        assert queued.status_code == 201, queued.text
        assert queued.json()["message"]["delivery"] == {
            "state": "sending",
            "failure_reason": None,
            "attempts": 0,
            "next_attempt_at": None,
            "delivered_at": None,
        }
        [card_reply] = [
            message
            for message in cabinet.card(reply.conversation_id)["messages"]
            if message["author"] == "staff"
        ]
        assert card_reply["delivery"]["state"] == "sending"
        assert [
            message["delivery"]
            for message in cabinet.card(reply.conversation_id)["messages"][:2]
        ] == [None, None]
        assert [empty.status_code, long.status_code] == [422, 422]
        assert [stranger.status_code, unknown.status_code] == [404, 404]
        assert len(world.messages(reply.conversation_id)) == 3
        assert len(cabinet.storage.outbox.queued()) == 1
