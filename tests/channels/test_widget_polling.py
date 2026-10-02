"""GET /v1/widget/{business_id}/messages: answers the widget has not shown yet."""

from typing import Any

from base_pydantic_schemas import PersistentDocument
from fastapi.testclient import TestClient

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import HttpResponse
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed

OTHER_VISITOR: str = "v1_someone_else_entirely_42"


def send(client: TestClient, business_id: BusinessId, text: str) -> dict[str, Any]:
    response = client.post(
        f"/v1/widget/{business_id}/messages",
        json={"session_key": SESSION_KEY, "text": text},
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def poll(
    client: TestClient,
    business_id: BusinessId,
    after: str | None = None,
    session_key: str = SESSION_KEY,
) -> HttpResponse:
    params: dict[str, str] = {} if after is None else {"after": after}
    return client.get(
        f"/v1/widget/{business_id}/messages",
        params=params,
        headers={"X-Widget-Session-Key": session_key},
    )


def add_staff_message(
    testbed: ChannelsTestbed,
    business_id: BusinessId,
    conversation_id: ConversationId,
    text: str,
    language: str = "he",
) -> MessageDocument:
    testbed.clock.advance(5)
    now = testbed.clock.now_microseconds()
    message = MessageDocument(
        conversation_id=conversation_id,
        business_id=business_id,
        direction=MessageDirection.OUTBOUND,
        author=MessageAuthor.STAFF,
        text=MessageText(text),
        language=LanguageTag(language),
        created_at=now,
        updated_at=now,
    )
    testbed.message_repo.save(message)
    return message


class TestWidgetPolling:
    def test_staff_replies_after_a_handoff_reach_the_widget(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        testbed.pipeline.is_silent = True
        reply = send(client, business.id, "אני רוצה לדבר עם מישהו")
        assert reply["is_handed_off"] is True

        nothing_yet = poll(client, business.id, after=reply["cursor"])
        assert nothing_yet.status_code == 200
        assert nothing_yet.headers["Access-Control-Allow-Origin"] == "*"
        assert nothing_yet.json() == {
            "items": [],
            "cursor": reply["cursor"],
            "has_more": False,
            "is_handed_off": True,
        }

        staff = add_staff_message(
            testbed, business.id, testbed.pipeline.conversation_id, "שלום, כאן דנה"
        )
        body = poll(client, business.id, after=reply["cursor"]).json()

        assert body["items"] == [
            {
                "id": str(staff.id),
                "author": "staff",
                "text": "שלום, כאן דנה",
                "language": "he",
                "direction": "rtl",
                "created_at": int(staff.created_at),
            }
        ]
        assert body["cursor"] == str(staff.id)
        assert body["is_handed_off"] is True
        assert poll(client, business.id, after=body["cursor"]).json()["items"] == []

    def test_the_answer_comes_again_after_the_reply_cursor_with_its_id(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        reply = send(client, business.id, "Hi")

        body = poll(client, business.id, after=reply["cursor"]).json()

        assert [item["id"] for item in body["items"]] == [reply["message_id"]]
        assert body["items"][0]["author"] == "assistant"
        assert body["cursor"] == reply["message_id"]
        assert body["is_handed_off"] is False

    def test_customer_messages_and_other_visitors_are_never_returned(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        first = send(client, business.id, "Hi")
        send(client, business.id, "And another thing")
        other = ConversationDocument(
            business_id=business.id,
            contact_id=ContactId(),
            assistant_version_id=AssistantVersionId(),
            channel=ChannelKind.WEB_CHAT,
            channel_user_id=ChannelUserId(OTHER_VISITOR),
            last_message_at=testbed.clock.now_microseconds(),
            created_at=testbed.clock.now_microseconds(),
            updated_at=testbed.clock.now_microseconds(),
        )
        testbed.conversation_repo.save(other)
        foreign = add_staff_message(
            testbed, business.id, other.id, "For someone else", "en"
        )

        body = poll(client, business.id, after=first["cursor"]).json()

        assert [item["text"] for item in body["items"]] == [
            "Reply: Hi",
            "Reply: And another thing",
        ]
        assert all(item["author"] == "assistant" for item in body["items"])
        assert poll(client, business.id, session_key=OTHER_VISITOR).json() == {
            "items": [],
            "cursor": str(foreign.id),
            "has_more": False,
            "is_handed_off": False,
        }
        assert poll(
            client, business.id, session_key="v1_nobody_has_written_yet"
        ).json() == {
            "items": [],
            "cursor": None,
            "has_more": False,
            "is_handed_off": False,
        }

    def test_without_a_known_position_only_the_current_one_is_returned(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        reply = send(client, business.id, "Hi")

        fresh = poll(client, business.id).json()
        erased = poll(client, business.id, after=str(MessageId())).json()

        # The position is the visitor's own latest message, so an answer the
        # widget missed (the page was left while it was written) comes next.
        assert fresh == {
            "items": [],
            "cursor": reply["cursor"],
            "has_more": False,
            "is_handed_off": False,
        }
        assert erased == fresh

    def test_an_answer_the_widget_missed_comes_after_the_position(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        reply = send(client, business.id, "Do you deliver to Batumi?")

        position = poll(client, business.id).json()
        missed = poll(client, business.id, after=position["cursor"]).json()

        assert position["items"] == []
        assert [item["id"] for item in missed["items"]] == [reply["message_id"]]
        assert missed["items"][0]["text"] == "Reply: Do you deliver to Batumi?"

    def test_long_backlogs_come_in_pages(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        testbed.pipeline.is_silent = True
        reply = send(client, business.id, "Hello?")
        for number in range(55):
            add_staff_message(
                testbed,
                business.id,
                testbed.pipeline.conversation_id,
                f"Note {number}",
            )

        first = poll(client, business.id, after=reply["cursor"]).json()
        second = poll(client, business.id, after=first["cursor"]).json()

        assert len(first["items"]) == 50
        assert first["has_more"] is True
        assert first["cursor"] == first["items"][-1]["id"]
        assert [item["text"] for item in second["items"]] == [
            f"Note {number}" for number in range(50, 55)
        ]
        assert second["has_more"] is False

    def test_a_resolved_handoff_is_reported(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        testbed.pipeline.is_silent = True
        reply = send(client, business.id, "Help")
        conversation = testbed.conversation_repo.get(
            business.id, testbed.pipeline.conversation_id
        )
        assert conversation is not None
        conversation.status = ConversationStatus.OPEN
        testbed.conversation_repo.save(conversation)

        body = poll(client, business.id, after=reply["cursor"]).json()

        assert body["is_handed_off"] is False

    def test_closed_chats_and_bad_queries_are_refused(self) -> None:
        testbed = ChannelsTestbed()
        owner_id = testbed.add_user("owner")
        business = testbed.add_business(owner_id)
        testbed.add_channel(
            business.id, ChannelKind.WEB_CHAT, status=ChannelStatus.DISABLED
        )
        open_business = enable_widget(testbed)
        client = testbed.build_http_client()

        closed = poll(client, business.id)
        unknown = poll(client, BusinessId())
        bad_key = poll(client, open_business.id, session_key="short")
        bad_after = poll(client, open_business.id, after="not an id")
        missing_key = client.get(f"/v1/widget/{open_business.id}/messages")

        assert closed.status_code == 404
        assert unknown.status_code == 404
        assert bad_key.status_code == 422
        assert bad_after.status_code == 422
        assert missing_key.status_code == 422


class CountingCollection[StoredDocument: PersistentDocument](
    InMemoryDocumentCollectionAdapter[StoredDocument]
):
    """Counts the documents every read returns."""

    def __init__(self, document_type: type[StoredDocument]) -> None:
        super().__init__(document_type)
        self.read_count: int = 0

    def list_all(self) -> list[StoredDocument]:
        documents = super().list_all()
        self.read_count += len(documents)
        return documents

    def list_by_field(self, field_name: str, value: str) -> list[StoredDocument]:
        documents = super().list_by_field(field_name, value)
        self.read_count += len(documents)
        return documents


class TestWidgetPollingCost:
    def test_a_poll_reads_only_the_visitors_conversations_and_messages(self) -> None:
        testbed = ChannelsTestbed()
        conversations = CountingCollection(ConversationDocument)
        messages = CountingCollection(MessageDocument)
        testbed.conversation_repo._collection = conversations  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        testbed.message_repo._collection = messages  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        for number in range(50):
            other = ConversationDocument(
                business_id=business.id,
                contact_id=ContactId(),
                assistant_version_id=AssistantVersionId(),
                channel=ChannelKind.WEB_CHAT,
                channel_user_id=ChannelUserId(f"v1_other_visitor_{number:04d}"),
                last_message_at=testbed.clock.now_microseconds(),
                created_at=testbed.clock.now_microseconds(),
                updated_at=testbed.clock.now_microseconds(),
            )
            testbed.conversation_repo.save(other)
            for note in range(20):
                add_staff_message(testbed, business.id, other.id, f"Note {note}", "en")
        reply = send(client, business.id, "Hi")
        conversations.read_count = messages.read_count = 0

        body = poll(client, business.id, after=reply["cursor"]).json()

        assert [item["id"] for item in body["items"]] == [reply["message_id"]]
        assert conversations.read_count == 1
        assert messages.read_count == 2
        conversations.read_count = messages.read_count = 0
        assert (
            poll(client, business.id, session_key=OTHER_VISITOR).json()["items"] == []
        )
        assert (conversations.read_count, messages.read_count) == (0, 0)

    def test_polling_too_fast_is_rate_limited(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        reply = send(client, business.id, "Hi")

        answers = [
            poll(client, business.id, after=reply["cursor"]).status_code
            for _ in range(61)
        ]
        other_visitor = poll(client, business.id, session_key=OTHER_VISITOR)

        assert answers[:60] == [200] * 60
        assert answers[60] == 429
        assert other_visitor.status_code == 200
        limited = poll(client, business.id, after=reply["cursor"])
        assert limited.json()["error"] == "rate_limited"
        assert limited.headers["Retry-After"] == "60"
        testbed.clock.advance(61)
        assert poll(client, business.id, after=reply["cursor"]).status_code == 200

    def test_the_visitor_key_travels_in_a_header_not_in_the_url(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        reply = send(client, business.id, "Hi")
        path = f"/v1/widget/{business.id}/messages"

        in_the_url = client.get(
            path, params={"session_key": SESSION_KEY, "after": reply["cursor"]}
        )
        preflight = client.options(
            path,
            headers={
                "Origin": "https://shop.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-widget-session-key",
            },
        )

        assert in_the_url.status_code == 422
        assert preflight.status_code == 204
        assert "x-widget-session-key" in (
            preflight.headers["Access-Control-Allow-Headers"].lower()
        )
        assert poll(client, business.id, after=reply["cursor"]).status_code == 200
