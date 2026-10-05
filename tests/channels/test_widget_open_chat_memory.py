"""
Widget polls remember a web chat they found open for a few seconds
(`OpenChatMemory`), so the polls of an open chat do not read its channel
every time: a chat switched off stops answering within that time, a chat
switched on answers at once.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFieldOrder
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.channels.open_chat_memory import (
    OPEN_CHAT_MEMORY_SECONDS,
    OpenChatMemory,
)
from tests.channels.test_widget import enable_widget
from tests.channels.testbed import ChannelsTestbed
from tests.channels.widget_polling_steps import poll, send

SECOND: int = 1_000_000


class CountingChannels(InMemoryDocumentCollectionAdapter[ChannelDocument]):
    """Counts the lookups of channels (a business's channels are one each)."""

    def __init__(self) -> None:
        super().__init__(ChannelDocument)
        self.lookup_count: int = 0

    def list_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        order: DocumentFieldOrder | None = None,
        limit: DocumentQueryLimit | None = None,
    ) -> list[ChannelDocument]:
        self.lookup_count += 1
        return super().list_by_fields(matches, order, limit)


def counted_testbed() -> tuple[ChannelsTestbed, CountingChannels]:
    testbed = ChannelsTestbed()
    channels = CountingChannels()
    testbed.channel_repo._collection = channels  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    return testbed, channels


def switch_widget(testbed: ChannelsTestbed, business_id: BusinessId, on: bool) -> None:
    channel = next(
        channel
        for channel in testbed.channel_repo.list_by_business(business_id)
        if channel.kind is ChannelKind.WEB_CHAT
    )
    channel.status = ChannelStatus.CONNECTED if on else ChannelStatus.DISABLED
    testbed.channel_repo.save(channel)


class TestOpenChatMemory:
    def test_polls_of_an_open_chat_read_its_channel_once_per_memory(self) -> None:
        testbed, channels = counted_testbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        reply = send(testbed, business.id, "Hi")
        channels.lookup_count = 0

        answers = [
            poll(client, business.id, after=reply["cursor"]).status_code
            for _ in range(5)
        ]
        lookups_while_remembered = channels.lookup_count
        testbed.clock.advance(OPEN_CHAT_MEMORY_SECONDS)
        later = poll(client, business.id, after=reply["cursor"])

        assert answers == [200] * 5
        assert lookups_while_remembered == 1
        assert later.status_code == 200
        assert channels.lookup_count == 2

    def test_a_chat_switched_off_stops_answering_within_the_memory(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        reply = send(testbed, business.id, "Hi")
        assert poll(client, business.id, after=reply["cursor"]).status_code == 200

        switch_widget(testbed, business.id, on=False)
        testbed.clock.advance(OPEN_CHAT_MEMORY_SECONDS - 1)
        remembered = poll(client, business.id, after=reply["cursor"])
        testbed.clock.advance(1)
        expired = poll(client, business.id, after=reply["cursor"])

        assert remembered.status_code == 200
        assert expired.status_code == 404
        assert expired.json()["error"] == "not_found"

    def test_a_closed_chat_is_never_remembered(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        switch_widget(testbed, business.id, on=False)
        client = testbed.build_http_client()

        closed = poll(client, business.id)
        switch_widget(testbed, business.id, on=True)
        opened = poll(client, business.id)

        assert closed.status_code == 404
        assert opened.status_code == 200


def test_the_memory_keeps_each_chat_for_its_time_and_forgets_on_demand() -> None:
    memory = OpenChatMemory()
    first, second = BusinessId(), BusinessId()
    start = Microseconds(1_790_000_000 * SECOND)
    memory.remember_open(first, start)
    memory.remember_open(second, start)
    memory.forget(second)
    end = Microseconds(int(start) + OPEN_CHAT_MEMORY_SECONDS * SECOND)

    assert memory.is_open(first, start)
    assert memory.is_open(first, Microseconds(int(end) - 1))
    assert not memory.is_open(first, end)
    assert not memory.is_open(second, start)
    assert not memory.is_open(BusinessId(), start)
