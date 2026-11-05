"""
Two API processes and two workers on one Postgres database, as
`render.yaml` runs them: the last free table goes to exactly one booking,
the widget's limits are counted once for both API processes, and one
customer's messages are answered one at a time whichever process receives
them and whichever worker answers them.
"""

import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.two_process_world import (
    SeededRestaurant,
    api_processes,
    read_model_calls,
    seed_restaurant,
    worker_processes,
)

# The restaurant has one table kind with three units (tests/e2e/journeys.py).
ANSWER_SECONDS: float = 60.0
TABLE_UNITS: int = 3
RACE_HOURS: tuple[int, ...] = (12, 14, 16, 18, 20)
RACERS_PER_HOUR: int = 10
WIDGET_MESSAGES_PER_VISITOR: int = 12


class TwoProcesses:
    def __init__(
        self,
        restaurant: SeededRestaurant,
        urls: list[str],
        call_log: Path,
        postgres_server: ThrowawayPostgresServer,
        database_name: str,
    ) -> None:
        self.restaurant = restaurant
        self.urls = urls
        self.call_log = call_log
        self.postgres_server = postgres_server
        self.database_name = database_name

    def url(self, index: int) -> str:
        """The processes take turns: request `index` goes to one of them."""

        return self.urls[index % len(self.urls)]


# Seeding opens the restaurant through the whole e2e journey and the API
# processes take seconds to start: one world for the module.
@pytest.fixture(scope="module")
def two_processes(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[TwoProcesses]:
    database_name = postgres_server.create_database(
        template_name=migrated_template_database
    )
    database_url = str(postgres_server.app_database_url(database_name))
    directory = tmp_path_factory.mktemp("two-processes")
    call_log = directory / "model-calls.log"
    try:
        restaurant = seed_restaurant(database_url)
        with (
            api_processes(database_url, call_log) as urls,
            worker_processes(database_url, call_log, directory, count=2),
        ):
            yield TwoProcesses(
                restaurant, urls, call_log, postgres_server, database_name
            )
    finally:
        postgres_server.drop_database(database_name)


def book(
    world: TwoProcesses, index: int, booking_date: str, booking_time: str
) -> httpx.Response:
    return httpx.post(
        f"{world.url(index)}{world.restaurant.base}/bookings",
        json={
            "contact_name": f"Гость {index}",
            "date": booking_date,
            "time": booking_time,
            "party_size": 2,
        },
        headers=world.restaurant.headers,
        timeout=60,
    )


def send_widget_message(
    world: TwoProcesses, index: int, session_key: str, text: str
) -> httpx.Response:
    return httpx.post(
        f"{world.url(index)}/v1/widget/{world.restaurant.business_id}/messages",
        json={"session_key": session_key, "text": text},
        timeout=120,
    )


def wait_for_model_calls(
    world: TwoProcesses, count: int
) -> list[tuple[int, float, float]]:
    """The model calls once the workers made `count` of them (all, at most)."""

    deadline = time.monotonic() + ANSWER_SECONDS
    while len(read_model_calls(world.call_log)) < count and time.monotonic() < deadline:
        time.sleep(0.2)

    return read_model_calls(world.call_log)


def wait_until_inbox_answered(world: TwoProcesses) -> bool:
    """True once no customer message waits in the job queue."""

    deadline = time.monotonic() + ANSWER_SECONDS
    while time.monotonic() < deadline:
        with world.postgres_server.admin_connection(world.database_name) as connection:
            row = connection.execute(
                "select count(*) from workshop.queued_jobs "
                "where document ->> 'name' = 'process_inbound_message' "
                "and document ->> 'status' in ('pending', 'running')"
            ).fetchone()
        if row is not None and int(row[0]) == 0:
            return True
        time.sleep(0.2)

    return False


def read_transcript_authors(world: TwoProcesses, session_key: str) -> list[str]:
    """The authors of one widget visitor's messages, in stored order."""

    with world.postgres_server.admin_connection(world.database_name) as connection:
        return [
            str(row[0])
            for row in connection.execute(
                "select m.document ->> 'author' from workshop.messages m "
                "join workshop.conversations c "
                "on c.document_key = m.document ->> 'conversation_id' "
                "where c.document ->> 'channel_user_id' = %s "
                "order by m.row_sequence",
                (session_key,),
            ).fetchall()
        ]


def wait_for_transcript(
    world: TwoProcesses, session_key: str, replies: int
) -> list[str]:
    """The visitor's transcript once `replies` assistant replies are stored."""

    deadline = time.monotonic() + ANSWER_SECONDS
    authors = read_transcript_authors(world, session_key)
    while authors.count("assistant") < replies and time.monotonic() < deadline:
        time.sleep(0.2)
        authors = read_transcript_authors(world, session_key)

    return authors


def outside_a_minute_boundary() -> None:
    """Let a burst of requests fall into one minute of the rate limits."""

    while time.time() % 60 > 45:
        time.sleep(0.5)


def test_the_last_free_tables_go_to_exactly_as_many_bookings(
    two_processes: TwoProcesses,
) -> None:
    booking_date = (datetime.now(UTC) + timedelta(days=3)).date().isoformat()
    times = [f"{hour}:00" for hour in RACE_HOURS]

    def race_for(booking_time: str) -> list[httpx.Response]:
        """More guests than tables at one hour, half of them in each process."""

        def guest(index: int) -> httpx.Response:
            return book(two_processes, index, booking_date, booking_time)

        with ThreadPoolExecutor(max_workers=RACERS_PER_HOUR) as pool:
            return list(pool.map(guest, range(RACERS_PER_HOUR)))

    races = [race_for(booking_time) for booking_time in times]

    for race in races:
        statuses = [racer.status_code for racer in race]
        assert statuses.count(201) == TABLE_UNITS, [racer.text for racer in race]
        assert set(statuses) <= {201, 409, 422}, statuses
    listed = httpx.get(
        f"{two_processes.url(0)}{two_processes.restaurant.base}/bookings",
        params={"from": booking_date, "to": booking_date, "limit": "100"},
        headers=two_processes.restaurant.headers,
        timeout=30,
    )
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["items"]) == TABLE_UNITS * len(times)


def test_the_widget_limit_is_counted_once_for_both_processes(
    two_processes: TwoProcesses,
) -> None:
    outside_a_minute_boundary()
    session_key = "visitor_limit_shared_0001"
    calls_before = len(read_model_calls(two_processes.call_log))

    def ask(index: int) -> httpx.Response:
        return send_widget_message(two_processes, index, session_key, f"Вопрос {index}")

    with ThreadPoolExecutor(max_workers=16) as pool:
        answers = list(pool.map(ask, range(WIDGET_MESSAGES_PER_VISITOR + 6)))

    statuses = [answer.status_code for answer in answers]
    # Counted per process, each would let 12 through: 18 in all.
    assert statuses.count(202) == WIDGET_MESSAGES_PER_VISITOR, statuses
    assert statuses.count(429) == 6
    refused = next(answer for answer in answers if answer.status_code == 429)
    assert int(refused.headers["Retry-After"]) >= 1
    # The workers answer every accepted message, one after another.
    assert wait_until_inbox_answered(two_processes)
    assert len(read_model_calls(two_processes.call_log)) > calls_before


def test_one_customers_messages_are_answered_one_at_a_time(
    two_processes: TwoProcesses,
) -> None:
    session_key = "visitor_serial_turns_0001"
    calls_before = len(read_model_calls(two_processes.call_log))

    def write(index: int) -> httpx.Response:
        return send_widget_message(
            two_processes, index, session_key, f"Сообщение {index}"
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(write, range(4)))

    # Both API processes took messages; the workers answer them.
    assert [answer.status_code for answer in answers] == [202] * 4
    calls = wait_for_model_calls(two_processes, calls_before + 4)[calls_before:]
    # No turn's model call overlapped another.
    assert len(calls) == 4
    for (_, _, previous_end), (_, next_start, _) in zip(calls, calls[1:], strict=False):
        assert next_start >= previous_end - 0.001
    # A call is logged as the model answers; its reply is stored after the
    # checks, before the turn's job is done: wait for the fourth stored reply
    # (an empty queue alone can be seen before the last reply commits).
    authors = wait_for_transcript(two_processes, session_key, replies=4)
    assert wait_until_inbox_answered(two_processes)
    # The transcript alternates: every reply follows its own message.
    assert authors == ["customer", "assistant"] * 4
