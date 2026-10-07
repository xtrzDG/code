"""
The world of the kill test: the e2e restaurant with its Telegram bot on the
test database (seeded in this process, on the real clock), one API process
taking the bot's webhooks, and customer workers (`kill_test_worker`)
started with the roles of render.yaml's `workshop-worker`.
"""

import subprocess
import sys
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.e2e.harness import bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import BUSINESS_BOT_TOKEN, open_restaurant
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import PROJECT_ROOT_DIRECTORY
from tests.storage.two_process_world import (
    stop_processes,
    use_the_real_clock,
    worker_environment,
)

STARTUP_SECONDS: float = 90.0
CUSTOMER_WORKER_ENVIRONMENT: dict[str, str] = {
    "WORKER_LANES": "inbound,outbound",
    "WORKER_POLL_SECONDS": "1",
    "WORKER_INBOUND_POLL_SECONDS": "1",
    # No "one moment" while the first model call hangs.
    "CHAT_TURN_DEADLINE_SECONDS": "600",
}


@dataclass(frozen=True)
class TelegramBot:
    """The restaurant's connected bot: where its webhooks go, signed how."""

    business_id: str
    webhook_path: str
    secret: str


@dataclass(frozen=True)
class KillWorld:
    bot: TelegramBot
    api_url: str
    workers: list[subprocess.Popen[bytes]]
    directory: Path
    postgres_server: ThrowawayPostgresServer
    database_name: str


def seed_telegram_restaurant(database_url: str) -> TelegramBot:
    """Open the e2e restaurant and connect its Telegram bot (recorded HTTP)."""

    workshop = start_workshop(
        {**E2E_ENVIRONMENT, "DATABASE_URL": database_url},
        prepare=use_the_real_clock,
    )
    with workshop.client as client:
        restaurant = open_restaurant(workshop)
        connected = client.put(
            f"/v1/businesses/{restaurant.business_id}/channels/telegram",
            json={"bot_token": BUSINESS_BOT_TOKEN},
            headers=bearer(restaurant.owner_token),
        )
        assert connected.status_code == 200, connected.text

    return TelegramBot(
        business_id=restaurant.business_id,
        webhook_path=f"/v1/channels/telegram/{connected.json()['id']}/webhook",
        secret=str(
            derive_telegram_webhook_secret(
                PlatformSecret(E2E_ENVIRONMENT["ENCRYPTION_KEY"]),
                ChannelSecret(BUSINESS_BOT_TOKEN),
            )
        ),
    )


def wait_for(is_done: Callable[[], bool], seconds: float = STARTUP_SECONDS) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if is_done():
            return
        time.sleep(0.1)

    raise AssertionError("Timed out waiting for the kill test's world.")


def read_log(log: Path) -> str:
    return log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""


def has_started(log: Path) -> bool:
    """The worker's lanes are taking jobs."""

    return "Worker lanes started" in read_log(log)


@contextmanager
def customer_workers(
    database_url: str, directory: Path, count: int, lease_seconds: int
) -> Generator[list[subprocess.Popen[bytes]]]:
    """`count` customer workers, each started and listening for jobs."""

    logs: list[Path] = [directory / f"worker-{index}.log" for index in range(count)]
    handles = [log.open("wb") for log in logs]
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tests.storage.kill_test_worker",
                str(directory),
                str(lease_seconds),
            ],
            cwd=PROJECT_ROOT_DIRECTORY,
            env=worker_environment(database_url, CUSTOMER_WORKER_ENVIRONMENT),
            stderr=handle,
            stdout=handle,
        )
        for handle in handles
    ]
    try:
        for log in logs:
            wait_for(partial(has_started, log))
        yield processes
    finally:
        stop_processes(processes)
        for handle in handles:
            handle.close()


def customer_messages(world: KillWorld, chat_id: str) -> list[tuple[str, str, str]]:
    """(author, message id, conversation id) of a customer's messages."""

    with world.postgres_server.admin_connection(world.database_name) as connection:
        return [
            (str(row[0]), str(row[1]), str(row[2]))
            for row in connection.execute(
                "select m.document ->> 'author', m.document_key, c.document_key "
                "from workshop.messages m join workshop.conversations c "
                "on c.document_key = m.document ->> 'conversation_id' "
                "where c.document ->> 'channel_user_id' = %s "
                "order by m.row_sequence",
                (chat_id,),
            ).fetchall()
        ]


def outbound_rows(world: KillWorld, conversation_id: str) -> list[tuple[str, str]]:
    """(the stored reply it sends, status) of each outbound row of a conversation."""

    with world.postgres_server.admin_connection(world.database_name) as connection:
        return [
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                "select document ->> 'source_message_id', document ->> 'status' "
                "from workshop.outbound_messages "
                "where document ->> 'conversation_id' = %s",
                (conversation_id,),
            ).fetchall()
        ]
