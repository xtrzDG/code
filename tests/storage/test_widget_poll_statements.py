"""
What a widget poll costs the database, counted (`statement_trace`) on the
real application over a small load dataset: the guard of the poll's
headroom (docs/operations/capacity.md, "The runs of 2026-10-19 and
2026-10-20").

A poll is two round trips whether it finds nothing new or a new answer:
the visitor's and network's rate-limit count (one statement), then the
poll's read (the scope and one statement, pipelined). The business and
platform counters come from the process's leases (a top-up every 60 and
600 polls), the open chat from `OpenChatMemory`. Before 2026-10-22 a poll
was 8 round trips and 8 statements in 3 transactions (9 and 9 with a new
answer). A poll may get cheaper; raise a budget only with the reason in
capacity.md.
"""

from collections.abc import Generator

import pytest
from httpx2 import Response
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.load_data import LoadWidgetVisitor
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from tests.storage.postgres_roles import RoleDatabase, role_database
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.request_cost_world import RequestCostWorld, open_request_cost_world
from tests.storage.statement_trace import TraceCount

POLL_ROUND_TRIPS: int = 2
POLL_STATEMENTS: int = 3
POLLS_IN_A_ROW: int = 5


@pytest.fixture(scope="module")
def world(
    postgres_server: ThrowawayPostgresServer, migrated_template_database: str
) -> Generator[RequestCostWorld]:
    database_name: str = postgres_server.create_database(
        template_name=migrated_template_database
    )
    role_urls: RoleDatabase = role_database(postgres_server, database_name)
    opened: RequestCostWorld = open_request_cost_world(role_urls)
    try:
        yield opened
    finally:
        opened.pools.close()
        postgres_server.drop_database(database_name)


def poll(world: RequestCostWorld, visitor: LoadWidgetVisitor) -> Response:
    """A poll from the visitor's last known message (the k6 scenario's)."""

    entry = world.business
    return world.client.get(
        f"/v1/widget/{entry.business_id}/messages",
        params={"after": str(visitor.latest_message_id)},
        headers={
            "X-Widget-Session-Key": str(visitor.session_key),
            "Origin": "https://cafe.example",
        },
    )


def answer_visitor(
    world: RequestCostWorld, visitor: LoadWidgetVisitor
) -> MessageDocument:
    """The assistant answers after the visitor's last known message."""

    business_id = world.business.business_id
    container = world.workshop.container
    with container.utilities.storage_scope().scoped_to_business(business_id):
        latest = container.repositories.message_repo().get(
            business_id, visitor.latest_message_id
        )
        assert latest is not None
        conversation = container.repositories.conversation_repo().list_by_channel_user(
            business_id, ChannelKind.WEB_CHAT, ChannelUserId(str(visitor.session_key))
        )[0]
        reply = MessageDocument(
            conversation_id=conversation.id,
            business_id=business_id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.ASSISTANT,
            text=MessageText("We have a table at eight."),
            created_at=Microseconds(int(latest.created_at) + 1_000_000),
            updated_at=Microseconds(int(latest.created_at) + 1_000_000),
        )
        container.repositories.message_repo().save(reply)
    return reply


def test_a_poll_that_finds_nothing_new_is_two_round_trips(
    world: RequestCostWorld,
) -> None:
    visitor = world.business.visitors[0]

    count: TraceCount = world.cost(lambda w: poll(w, visitor))
    answer = poll(world, visitor).json()

    assert answer["items"] == []
    assert answer["cursor"] == str(visitor.latest_message_id)
    assert count.round_trips <= POLL_ROUND_TRIPS, count
    assert count.statements <= POLL_STATEMENTS, count


def test_a_poll_that_finds_a_new_answer_is_two_round_trips(
    world: RequestCostWorld,
) -> None:
    visitor = world.business.visitors[1]
    reply = answer_visitor(world, visitor)

    count: TraceCount = world.cost(lambda w: poll(w, visitor))
    answer = poll(world, visitor).json()

    assert [item["id"] for item in answer["items"]] == [str(reply.id)]
    assert answer["cursor"] == str(reply.id)
    assert count.round_trips <= POLL_ROUND_TRIPS, count
    assert count.statements <= POLL_STATEMENTS, count


def test_polls_in_a_row_take_their_shared_counters_from_the_lease(
    world: RequestCostWorld,
) -> None:
    visitor = world.business.visitors[0]

    def polls(w: RequestCostWorld) -> Response:
        answers = [poll(w, visitor) for _ in range(POLLS_IN_A_ROW)]
        assert {answer.status_code for answer in answers} == {200}
        return answers[-1]

    count: TraceCount = world.cost(polls)

    assert count.round_trips <= POLLS_IN_A_ROW * POLL_ROUND_TRIPS, count
