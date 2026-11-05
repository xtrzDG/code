"""
Kill -9 one of two customer workers mid-turn, as render.yaml runs them (two
`workshop-worker` instances on the inbound and outbound lanes beside the
API, one Postgres): the other worker answers the customer within the job
lease plus 5 s, with exactly one outbound row for the reply, sent once.
"""

import json
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

from tests.storage.kill_test_worker import (
    FIRST_CALL_MARKER,
    MODEL_CALL_LOG,
    TELEGRAM_SENDS,
)
from tests.storage.kill_world import (
    KillWorld,
    customer_messages,
    customer_workers,
    outbound_rows,
    seed_telegram_restaurant,
    wait_for,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.two_process_api import REPLY
from tests.storage.two_process_world import api_processes, read_model_calls

# A short lease, so the test takes seconds; production's is 120 s.
LEASE_SECONDS: int = 6
TAKEOVER_GRACE_SECONDS: float = 5.0
CUSTOMER_CHAT: int = 9001
DELIVERY_SECONDS: float = 15.0


@pytest.fixture
def kill_world(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
    tmp_path: Path,
) -> Generator[KillWorld]:
    database_name = postgres_server.create_database(
        template_name=migrated_template_database
    )
    database_url = str(postgres_server.app_database_url(database_name))
    try:
        bot = seed_telegram_restaurant(database_url)
        with (
            api_processes(database_url, tmp_path / "api-calls.log", count=1) as urls,
            customer_workers(database_url, tmp_path, 2, LEASE_SECONDS) as workers,
        ):
            yield KillWorld(
                bot, urls[0], workers, tmp_path, postgres_server, database_name
            )
    finally:
        postgres_server.drop_database(database_name)


def customer_writes(world: KillWorld, text: str) -> None:
    delivered = httpx.post(
        f"{world.api_url}{world.bot.webhook_path}",
        json={
            "update_id": 1,
            "message": {
                "message_id": 101,
                "date": int(time.time()),
                "from": {"id": CUSTOMER_CHAT, "is_bot": False, "first_name": "N"},
                "chat": {"id": CUSTOMER_CHAT, "type": "private"},
                "text": text,
            },
        },
        headers={"X-Telegram-Bot-Api-Secret-Token": world.bot.secret},
        timeout=60,
    )
    assert delivered.status_code == 200, delivered.text


def hanging_worker(world: KillWorld) -> subprocess.Popen[bytes]:
    """The worker whose model call hangs: it is mid-turn."""

    marker = world.directory / FIRST_CALL_MARKER
    wait_for(marker.exists, seconds=60)
    pid = int(marker.read_text(encoding="utf-8"))
    [worker] = [process for process in world.workers if process.pid == pid]
    return worker


def answered_conversation(world: KillWorld) -> str | None:
    """The customer's conversation once its reply is stored and in the outbox."""

    messages = customer_messages(world, str(CUSTOMER_CHAT))
    replies = [message for message in messages if message[0] == "assistant"]
    if not replies or not outbound_rows(world, replies[0][2]):
        return None

    return replies[0][2]


def telegram_sends(world: KillWorld) -> list[dict[str, object]]:
    log = world.directory / TELEGRAM_SENDS
    if not log.exists():
        return []

    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def test_the_other_worker_answers_within_the_lease_with_one_outbound_row(
    kill_world: KillWorld,
) -> None:
    customer_writes(kill_world, "Есть столик на четверых сегодня?")
    victim = hanging_worker(kill_world)

    victim.kill()  # SIGKILL mid-turn: nothing is handed back, nothing cleaned up
    killed_at = time.monotonic()
    wait_for(
        lambda: answered_conversation(kill_world) is not None,
        seconds=LEASE_SECONDS + TAKEOVER_GRACE_SECONDS + 30,
    )
    answered_after = time.monotonic() - killed_at

    assert answered_after <= LEASE_SECONDS + TAKEOVER_GRACE_SECONDS, answered_after
    messages = customer_messages(kill_world, str(CUSTOMER_CHAT))
    assert [author for author, _, _ in messages] == ["customer", "assistant"]
    _, reply_id, conversation_id = messages[1]
    calls = read_model_calls(kill_world.directory / MODEL_CALL_LOG)
    assert {pid for pid, _, _ in calls} == {
        worker.pid for worker in kill_world.workers if worker is not victim
    }
    wait_for(lambda: bool(telegram_sends(kill_world)), seconds=DELIVERY_SECONDS)
    assert [source for source, _ in outbound_rows(kill_world, conversation_id)] == [
        reply_id
    ]
    # Sent once (after the assistant's first-message disclosure).
    [sent] = telegram_sends(kill_world)
    assert str(sent["text"]).endswith(REPLY)
    assert sent["pid"] != victim.pid
