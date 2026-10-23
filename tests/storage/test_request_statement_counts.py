"""
What the hot requests cost the database, counted (`statement_trace`): the
round trips (statements, a `begin; select set_config(...)` counting once)
of one request of each kind the latency budgets time (tests/perf), and the
transactions of a Telegram webhook. Counts do not depend on how busy the
machine is, so they guard the headroom the timings cannot: a change that
adds a read to every cabinet request fails here, on every pull request.

The budgets are the counts of 2026-10-12 (docs/operations/capacity.md,
"The weekly run of 2026-10-12"), down from: /v1/me 25, the conversation
list 42, a conversation 78, availability 49, the dashboard 81, a widget
poll 9 and a Telegram webhook 27 round trips in 4 transactions. Wave 19
added one each to /v1/me (the brands the person belongs to) and to the
conversation list and card (a repeated view's first count in
`audit_view_counts`); capacity.md says why. The widget poll went from 8 to
2 on 2026-10-22 (its count and one pipelined read; "The runs of
2026-10-19 and 2026-10-20" in capacity.md, and
`test_widget_poll_statements.py`). A request may get cheaper; raise a
budget only with the reason in capacity.md.
"""

from collections.abc import Callable, Generator

import pytest
from httpx2 import Response

from app.schemas.typings.platform.strings import DatabaseUrl
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.request_cost_world import (
    RequestCostWorld,
    check_availability,
    get_conversation,
    get_dashboard,
    get_me,
    list_conversations,
    open_request_cost_world,
    poll_widget,
    send_telegram_message,
)
from tests.storage.statement_trace import TraceCount

ROUND_TRIP_BUDGETS: dict[str, tuple[Callable[[RequestCostWorld], Response], int]] = {
    "authenticate (GET /v1/me)": (get_me, 12),
    "conversations_list": (list_conversations, 23),
    "conversation_detail": (get_conversation, 32),
    "availability": (check_availability, 21),
    "dashboard": (get_dashboard, 28),
    "widget_poll": (poll_widget, 2),
    "telegram_webhook": (send_telegram_message, 14),
}
# The channel's read, then dedupe, inbox row, job and wake-up in one.
TELEGRAM_WEBHOOK_TRANSACTIONS: int = 2


@pytest.fixture(scope="module")
def world(
    postgres_server: ThrowawayPostgresServer, migrated_template_database: str
) -> Generator[RequestCostWorld]:
    database_name: str = postgres_server.create_database(
        template_name=migrated_template_database
    )
    database_url: DatabaseUrl = postgres_server.app_database_url(database_name)
    opened: RequestCostWorld = open_request_cost_world(database_url)
    try:
        yield opened
    finally:
        opened.pool.close()
        postgres_server.drop_database(database_name)


@pytest.mark.parametrize("kind", list(ROUND_TRIP_BUDGETS))
def test_a_request_stays_within_its_round_trips(
    kind: str, world: RequestCostWorld
) -> None:
    send, budget = ROUND_TRIP_BUDGETS[kind]

    count: TraceCount = world.cost(send)

    assert 0 < count.round_trips <= budget, (
        f"{kind}: {count.round_trips} round trips to the database, "
        f"over its budget of {budget}"
    )


def test_a_telegram_webhook_stores_its_message_in_one_transaction(
    world: RequestCostWorld,
) -> None:
    count: TraceCount = world.cost(send_telegram_message)

    assert count.transactions <= TELEGRAM_WEBHOOK_TRANSACTIONS, (
        f"a Telegram webhook ran {count.transactions} transactions"
    )
