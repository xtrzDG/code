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
        assert cabinet.storage.outbox.sent == []
        assert cabinet.storage.outbox.templates == [
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

    def test_template_text_is_length_checked_and_a_refusal_stores_nothing(
        self,
    ) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send("Hi")
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WHATSAPP, staff_template=STAFF_TEMPLATE)
        world.clock.advance(timedelta(days=3))

        too_long = cabinet.reply(reply.conversation_id, "x" * 1025, as_template=True)
        just_fits = cabinet.reply(reply.conversation_id, "y " * 512, as_template=True)

        assert too_long.status_code == 422
        assert "1024" in too_long.json()["message"]
        assert just_fits.status_code == 201, just_fits.text
        [(_, _, _, [parameter])] = cabinet.storage.outbox.templates
        assert len(parameter) == 1023  # "y y ... y": line breaks and runs fold
        assert len(world.messages(reply.conversation_id)) == 3

    def test_a_template_reply_is_queued_in_the_owners_language_only(
        self,
    ) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send("Hi")
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.WHATSAPP, staff_template=STAFF_TEMPLATE)
        world.clock.advance(timedelta(hours=25))

        sent = cabinet.reply(reply.conversation_id, "Hello", as_template=True)

        # Whether Meta accepts the template is known when the worker sends
        # it: the reply shows "sending" until then (tests/channels covers a
        # refusal: the reply turns "failed" with the reason).
        assert sent.status_code == 201, sent.text
        assert sent.json()["delivery"] == "sent_as_template"
        assert sent.json()["message"]["delivery"]["state"] == "sending"
        [message] = cabinet.storage.outbox.queued()
        assert message.template is not None
        assert str(message.template.language_code) == "en_US"
        assert message.kind.value == "staff_reply"

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
        assert cabinet.storage.outbox.templates == []
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
        assert cabinet.storage.outbox.sent == [
            (ChannelKind.WHATSAPP, "995555123456", "Line one\nLine two")
        ]
        assert cabinet.storage.outbox.templates == []

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
        assert cabinet.storage.outbox.templates == []
