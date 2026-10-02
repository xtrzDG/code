"""The conversation feed's paging and filters, the card's linked items and
staff replies from the cabinet."""

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.schemas.constants.bookings import (
    BookingStatus,
    LeadType,
    ResourceKind,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
    ResourceCapacity,
)
from app.schemas.typings.bookings.strings import LeadDetails, ResourceName
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import BrainWorld, build_world, say, scripted
from tests.brain.cabinet_http import CabinetStorage, bearer, build_cabinet_client

DAY_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000
STAFF_TEMPLATE: WhatsAppStaffTemplate = WhatsAppStaffTemplate(
    name=WhatsAppTemplateName("staff_reply"),
    language_code=WhatsAppTemplateLanguageCode("en_US"),
)


class UnusedMenuExtractor:
    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        raise AssertionError("Menu extraction is not part of these tests.")


class Cabinet:
    def __init__(self, world: BrainWorld) -> None:
        self.world = world
        self.storage = CabinetStorage()
        self.client: TestClient = build_cabinet_client(
            world,
            UnusedMenuExtractor(),
            {"owner": world.owner_id, "staff": world.staff_id, "stranger": UserId()},
            self.storage,
        )

    def url(self, path: str = "") -> str:
        return f"/v1/businesses/{self.world.business.id}/conversations{path}"

    def feed(self, token: str = "staff", **params: str) -> dict[str, Any]:
        response = self.client.get(self.url(), params=params, headers=bearer(token))
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    def names(self, **params: str) -> list[str | None]:
        return [row["contact_name"] for row in self.feed(**params)["items"]]

    def card(self, conversation_id: ConversationId) -> dict[str, Any]:
        response = self.client.get(
            self.url(f"/{conversation_id}"), headers=bearer("owner")
        )
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    def reply(
        self,
        conversation_id: ConversationId,
        text: str,
        token: str = "staff",
        as_template: bool | None = None,
    ) -> Any:
        body: dict[str, Any] = {"text": text}
        if as_template is not None:
            body["as_template"] = as_template
        return self.client.post(
            self.url(f"/{conversation_id}/messages"),
            json=body,
            headers=bearer(token),
        )

    def connect(
        self,
        kind: ChannelKind,
        status: ChannelStatus = ChannelStatus.CONNECTED,
        staff_template: WhatsAppStaffTemplate | None = None,
    ) -> None:
        self.world.channel_repo.save(
            ChannelDocument(
                business_id=self.world.business.id,
                kind=kind,
                status=status,
                whatsapp_staff_template=staff_template,
            )
        )


def seed_feed(world: BrainWorld) -> dict[str, ConversationId]:
    """Four customers on three days, with names and texts in three scripts."""

    ids: dict[str, ConversationId] = {}
    ids["nino"] = world.send(
        "Столик на субботу?",
        name="Ниноʼ Беридзе",
        user_id="995599112233",
        phone=E164PhoneNumber("+995599112233"),
    ).conversation_id
    world.clock.advance(timedelta(days=1))
    ids["jose"] = world.send(
        "Hola, ¿tienen mesa?",
        channel=ChannelKind.TELEGRAM,
        user_id="tg-jose",
        name="José",
        phone=None,
    ).conversation_id
    world.clock.advance(timedelta(days=1))
    ids["giorgi"] = world.send(
        "გამარჯობა, ხინკალი გაქვთ?",
        user_id="995577001122",
        name="Giorgi",
        phone=None,
    ).conversation_id
    ids["test"] = world.send(
        "Sandbox", is_sandbox=True, user_id="autotest", phone=None
    ).conversation_id
    for conversation in world.conversations():
        if conversation.id == ids["nino"]:
            conversation.status = ConversationStatus.HANDOFF
            world.conversation_repo.save(conversation)

    return ids


def test_feed_pages_by_the_latest_message() -> None:
    world = build_world(scripted(*(say(f"Answer {n}") for n in range(4))))
    seed_feed(world)
    cabinet = Cabinet(world)

    first = cabinet.feed(limit="2")
    second = cabinet.feed(limit="2", cursor=first["next_cursor"])

    assert [row["contact_name"] for row in first["items"]] == ["Giorgi", "José"]
    assert [row["contact_name"] for row in second["items"]] == ["Ниноʼ Беридзе"]
    assert second["next_cursor"] is None


def test_feed_filters_by_status_channel_and_local_period() -> None:
    world = build_world(scripted(*(say(f"Answer {n}") for n in range(4))))
    seed_feed(world)
    cabinet = Cabinet(world)

    assert cabinet.names(status="handoff") == ["Ниноʼ Беридзе"]
    assert cabinet.names(channel="telegram") == ["José"]
    # The world starts on 2026-10-01 at 14:00 in Tbilisi.
    assert cabinet.names(**{"from": "2026-10-02", "to": "2026-10-02"}) == ["José"]
    assert cabinet.names(**{"from": "2026-10-02"}) == ["Giorgi", "José"]
    assert cabinet.names(to="2026-10-01") == ["Ниноʼ Беридзе"]
    assert len(cabinet.feed(include_sandbox="true")["items"]) == 4


def test_search_finds_names_phones_and_words_in_any_script() -> None:
    world = build_world(scripted(*(say(f"Answer {n}") for n in range(4))))
    seed_feed(world)
    cabinet = Cabinet(world)

    assert cabinet.names(search="нино") == ["Ниноʼ Беридзе"]
    assert cabinet.names(search="jose") == ["José"]
    assert cabinet.names(search="599 11-22-33") == ["Ниноʼ Беридзе"]
    assert cabinet.names(search="0599112233") == ["Ниноʼ Беридзе"]
    assert cabinet.names(search="ХИНКАЛИ") == []
    assert cabinet.names(search="ხინკალი") == ["Giorgi"]
    assert cabinet.names(search="mesa") == ["José"]
    assert cabinet.names(search="answer 1") == ["José"]
    assert cabinet.names(search="nobody here") == []
    assert cabinet.names(search="столик", channel="telegram") == []


def test_feed_rejects_bad_filters() -> None:
    world = build_world(scripted(say("Hi")))
    world.send("Hi")
    cabinet = Cabinet(world)

    for params in (
        {"status": "lost"},
        {"from": "2026-02-30"},
        {"from": "yesterday"},
        {"from": "2026-10-05", "to": "2026-10-01"},
        {"search": "x" * 201},
        {"limit": "0"},
        {"limit": "201"},
        {"cursor": "%%%"},
    ):
        response = cabinet.client.get(
            cabinet.url(), params=params, headers=bearer("owner")
        )
        assert response.status_code == 422, params


def test_card_lists_the_bookings_leads_and_handoffs_made_in_it() -> None:
    world = build_world(scripted(say("Да, есть."), say("Hello")))
    reply = world.send("Столик на вечер?", name="Нино")
    other = world.send("Hi", channel=ChannelKind.TELEGRAM, user_id="tg-1", phone=None)
    cabinet = Cabinet(world)
    conversation = next(
        item for item in world.conversations() if item.id == reply.conversation_id
    )
    table = ResourceDocument(
        business_id=world.business.id,
        kind=ResourceKind.TABLE,
        name=ResourceName("Table 4"),
        capacity=ResourceCapacity(4),
    )
    cabinet.storage.resource_repo.save(table)
    for conversation_id, hour in (
        (reply.conversation_id, 19),
        (other.conversation_id, 20),
    ):
        cabinet.storage.booking_repo.save(
            BookingDocument(
                business_id=world.business.id,
                resource_id=table.id,
                contact_id=conversation.contact_id,
                conversation_id=conversation_id,
                starts_at=BookingStartsAtUnixSeconds(1_791_219_600 + hour * 60),
                ends_at=BookingEndsAtUnixSeconds(1_791_226_800 + hour * 60),
                party_size=PartySize(2),
                status=BookingStatus.CONFIRMED,
                source_channel=ChannelKind.WHATSAPP,
            )
        )
    cabinet.storage.lead_repo.save(
        LeadDocument(
            business_id=world.business.id,
            contact_id=conversation.contact_id,
            conversation_id=reply.conversation_id,
            lead_type=LeadType.BANQUET,
            details=LeadDetails("Wedding for 60"),
            source_channel=ChannelKind.WHATSAPP,
        )
    )
    world.handoff_repo.save(
        HandoffDocument(
            business_id=world.business.id,
            conversation_id=reply.conversation_id,
            contact_id=conversation.contact_id,
            reason=HandoffReason.COMPLAINT,
            summary=HandoffSummary("Cold soup"),
        )
    )

    card = cabinet.card(reply.conversation_id)

    [booking] = card["bookings"]
    assert booking["resource_name"] == "Table 4"
    assert booking["contact_name"] == "Нино"
    assert booking["conversation_id"] == str(reply.conversation_id)
    assert [lead["details"] for lead in card["leads"]] == ["Wedding for 60"]
    assert [handoff["summary"] for handoff in card["handoffs"]] == ["Cold soup"]
    assert card["handoffs"][0]["contact_name"] == "Нино"
    assert cabinet.card(other.conversation_id)["leads"] == []


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
        assert cabinet.storage.channel_sender.sent == [
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
        assert len(cabinet.storage.channel_sender.sent) == 1

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
        assert cabinet.storage.channel_sender.sent == []
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
        assert cabinet.storage.channel_sender.sent == []

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
        assert cabinet.storage.channel_sender.sent == [
            (ChannelKind.TELEGRAM, "tg-9", "We are on it.")
        ]

    def test_failed_delivery_stores_nothing_and_bad_input_is_refused(self) -> None:
        world = build_world(scripted(say("Hello!")))
        reply = world.send(
            "Hi", channel=ChannelKind.TELEGRAM, user_id="tg-7", phone=None
        )
        cabinet = Cabinet(world)
        cabinet.connect(ChannelKind.TELEGRAM)
        cabinet.storage.channel_sender.failure = "Telegram is down."

        failed = cabinet.reply(reply.conversation_id, "Hello")
        empty = cabinet.reply(reply.conversation_id, "   ")
        long = cabinet.reply(reply.conversation_id, "x" * 4001)
        stranger = cabinet.reply(reply.conversation_id, "Hi", token="stranger")
        unknown = cabinet.reply(ConversationId(), "Hi")

        assert failed.status_code == 502
        assert [empty.status_code, long.status_code] == [422, 422]
        assert [stranger.status_code, unknown.status_code] == [404, 404]
        assert len(world.messages(reply.conversation_id)) == 2


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
