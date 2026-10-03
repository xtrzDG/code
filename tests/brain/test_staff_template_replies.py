"""Staff replies sent as the business's WhatsApp staff template."""

from datetime import timedelta

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.channels import WhatsAppStaffTemplate
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from tests.brain.brain_world import build_world
from tests.brain.conversation_cabinet_helpers import Cabinet
from tests.brain.scripted_turns import say, scripted

STAFF_TEMPLATE: WhatsAppStaffTemplate = WhatsAppStaffTemplate(
    name=WhatsAppTemplateName("staff_reply"),
    language_code=WhatsAppTemplateLanguageCode("en_US"),
)


class TestStaffRepliesAsWhatsAppTemplates:
    def test_after_24_hours_the_reply_goes_in_the_owners_template(self) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send("Hi")
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WHATSAPP, staff_template=STAFF_TEMPLATE)
        world.clock.advance(timedelta(hours=25))

        state = cabinet.card(reply.conversation_id)["reply"]
        plain = cabinet.reply(reply.conversation_id, "Hello again")
        sent = cabinet.reply(
            reply.conversation_id,
            "Your table is ready.\n\nSee you   at 20:00.",
            as_template=True,
        )

        assert state["is_available"] is False
        assert state["block"] == "window_closed"
        assert state["template"] == {
            "name": "staff_reply",
            "language_code": "en_US",
            "max_text_length": 1024,
        }
        assert plain.status_code == 409
        assert "template" in plain.json()["message"]
        assert sent.status_code == 201, sent.text
        assert sent.json()["delivery"] == "sent_as_template"
        message = sent.json()["message"]
        assert message["text"] == "Your table is ready. See you at 20:00."
        assert (message["author"], message["sent_by"]) == ("staff", str(world.staff_id))
        assert cabinet.storage.channel_sender.sent == []
        assert cabinet.storage.channel_sender.templates == [
            (
                "995555123456",
                "staff_reply",
                "en_US",
                ["Your table is ready. See you at 20:00."],
            )
        ]
        stored = world.messages(reply.conversation_id)
        assert stored[-1].text == "Your table is ready. See you at 20:00."
        audit = world.audit_log_repo.list_by_business(world.business.id)
        assert (audit[-1].action, audit[-1].entity) == (AuditAction.CREATE, "message")
        assert len(world.turns(reply.conversation_id)) == 2

    def test_template_text_is_length_checked_and_failures_store_nothing(
        self,
    ) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send("Hi")
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WHATSAPP, staff_template=STAFF_TEMPLATE)
        world.clock.advance(timedelta(days=3))

        too_long = cabinet.reply(reply.conversation_id, "x" * 1025, as_template=True)
        just_fits = "y " * 512
        cabinet.storage.channel_sender.failure = "WhatsApp refused the template."
        failed = cabinet.reply(reply.conversation_id, just_fits, as_template=True)

        assert too_long.status_code == 422
        assert "1024" in too_long.json()["message"]
        assert failed.status_code == 502
        assert cabinet.storage.channel_sender.templates == []
        assert len(world.messages(reply.conversation_id)) == 2

    def test_a_template_meta_refuses_is_a_conflict_naming_the_template(
        self,
    ) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send("Hi")
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WHATSAPP, staff_template=STAFF_TEMPLATE)
        world.clock.advance(timedelta(hours=25))
        cabinet.storage.channel_sender.template_rejection = (
            "Meta refused the message template (132001): (#132001) Template "
            "name does not exist in the translation"
        )

        refused = cabinet.reply(reply.conversation_id, "Hello", as_template=True)

        # Not "try again in a minute": retrying cannot help until the owner
        # corrects the template in the channel settings.
        assert refused.status_code == 409
        body = refused.json()
        assert body["error"] == "conflict"
        assert "template" in body["message"]
        [reason] = body["reasons"]
        assert reason["code"] == "template_rejected"
        assert "132001" in reason["message"]
        assert reason["details"] == ["staff_reply", "en_US"]
        assert cabinet.storage.channel_sender.templates == []
        assert len(world.messages(reply.conversation_id)) == 2

    def test_without_a_template_the_refusal_points_to_the_channels_page(
        self,
    ) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send("Hi")
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WHATSAPP)
        world.clock.advance(timedelta(hours=25))

        state = cabinet.card(reply.conversation_id)["reply"]
        refused = cabinet.reply(reply.conversation_id, "Hello", as_template=True)

        assert (state["block"], state["template"]) == ("window_closed", None)
        assert refused.status_code == 409
        assert "Channels page" in refused.json()["message"]
        assert cabinet.storage.channel_sender.templates == []
        assert len(world.messages(reply.conversation_id)) == 2

    def test_inside_the_window_a_template_request_is_an_ordinary_message(
        self,
    ) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send("Hi")
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WHATSAPP, staff_template=STAFF_TEMPLATE)
        world.clock.advance(timedelta(hours=2))

        state = cabinet.card(reply.conversation_id)["reply"]
        sent = cabinet.reply(
            reply.conversation_id, "Line one\nLine two", as_template=True
        )

        assert (state["is_available"], state["template"]) == (True, None)
        assert sent.status_code == 201
        assert sent.json()["delivery"] == "sent"
        assert cabinet.storage.channel_sender.sent == [
            (ChannelKind.WHATSAPP, "995555123456", "Line one\nLine two")
        ]
        assert cabinet.storage.channel_sender.templates == []

    def test_other_windowed_channels_and_disconnected_whatsapp_get_no_template(
        self,
    ) -> None:
        world = build_world(scripted(say("a"), say("b")))
        whatsapp = world.send("Hi")
        instagram = world.send(
            "Hi", channel=ChannelKind.INSTAGRAM, user_id="igsid-1", phone=None
        )
        cabinet = Cabinet(world)
        cabinet.connect(
            ChannelKind.WHATSAPP, ChannelStatus.DISABLED, staff_template=STAFF_TEMPLATE
        )
        cabinet.connect(ChannelKind.INSTAGRAM)
        world.clock.advance(timedelta(days=2))

        whatsapp_state = cabinet.card(whatsapp.conversation_id)["reply"]
        instagram_state = cabinet.card(instagram.conversation_id)["reply"]
        refused = cabinet.reply(whatsapp.conversation_id, "Hi", as_template=True)

        assert (whatsapp_state["block"], whatsapp_state["template"]) == (
            "channel_disconnected",
            None,
        )
        assert (instagram_state["block"], instagram_state["template"]) == (
            "window_closed",
            None,
        )
        assert refused.status_code == 409
        assert cabinet.storage.channel_sender.templates == []
