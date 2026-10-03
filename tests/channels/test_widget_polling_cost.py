"""GET /v1/widget/{business_id}/messages: what one poll costs in storage reads."""

from collections.abc import Sequence

from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFieldOrder
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed
from tests.channels.widget_polling_steps import (
    OTHER_VISITOR,
    add_staff_message,
    poll,
    send,
)


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

    def list_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        order: DocumentFieldOrder | None = None,
        limit: DocumentQueryLimit | None = None,
    ) -> list[StoredDocument]:
        documents = super().list_by_fields(matches, order, limit)
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
        reply = send(testbed, business.id, "Hi")
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
        reply = send(testbed, business.id, "Hi")

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
        # The next minute starts in 60 s; a second into it, this minute's
        # weight leaves room for one more.
        assert limited.headers["Retry-After"] == "61"
        testbed.clock.advance(61)
        assert poll(client, business.id, after=reply["cursor"]).status_code == 200

    def test_the_visitor_key_travels_in_a_header_not_in_the_url(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        reply = send(testbed, business.id, "Hi")
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
