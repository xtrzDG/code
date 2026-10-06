"""
A game day's world: the e2e restaurant on its own test database, API
processes and workers (`chaos_process.py`) on the shared movable clock,
the staff providers' record and, when asked, the fake providers. The test
breaks one thing, then reads what the outside sees: GET /healthz/pipeline,
GET /readyz, GET /v1/platform/status and the alerts the team got.
"""

import os
import subprocess
import sys
import time
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any, LiteralString, cast

import httpx

from tests.channels.channels_settings import META_APP_SECRET
from tests.chaos.chaos_clock import CLOCK_FILE_VARIABLE, ChaosClock
from tests.chaos.chaos_process import PROVIDER_URL_VARIABLE
from tests.chaos.chaos_sends import SENDS_FILE_VARIABLE, Sent, headlines
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.storage.kill_world import has_started, read_log
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import PROJECT_ROOT_DIRECTORY
from tests.storage.two_process_world import (
    SeededRestaurant,
    free_port,
    stop_processes,
    wait_until_ready,
)

STARTUP_SECONDS: float = 90.0
ALERT_CHAT: str = "-1009000000001"
WORKER_DOWN_TITLE: str = "No worker answers"
SECOND: float = 1.0
MINUTE: float = 60.0


def wait_for(
    is_done: Callable[[], bool], seconds: float = 30.0, what: str = "the world"
) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if is_done():
            return
        time.sleep(0.2)

    raise AssertionError(f"Timed out after {seconds:.0f} s waiting for {what}.")


@dataclass
class ChaosWorld:
    """One database, its processes and what they told the team."""

    postgres_server: ThrowawayPostgresServer
    database_name: str
    restaurant: SeededRestaurant
    directory: Path
    clock: ChaosClock
    provider_url: str | None = None
    environment: dict[str, str] = field(default_factory=dict[str, str])
    processes: list[subprocess.Popen[bytes]] = field(
        default_factory=list[subprocess.Popen[bytes]]
    )

    @property
    def database_url(self) -> str:
        return str(self.postgres_server.app_database_url(self.database_name))

    @property
    def sends_file(self) -> Path:
        return self.directory / "sends.jsonl"

    def process_environment(self, extra: Mapping[str, str]) -> dict[str, str]:
        environment: dict[str, str] = {
            "PATH": os.environ.get("PATH", ""),
            "APP_ENV": E2E_ENVIRONMENT["APP_ENV"],
            "ENCRYPTION_KEY": E2E_ENVIRONMENT["ENCRYPTION_KEY"],
            "DATABASE_URL": self.database_url,
            "LLM_PROVIDER": "scripted",
            "MESSAGE_COALESCE_SECONDS": "0",
            "DB_POOL_SIZE": "12",
            "THREADPOOL_SIZE": "12",
            "LOG_FORMAT": "json",
            "META_APP_SECRET": META_APP_SECRET,
            "PLATFORM_ALERT_TELEGRAM_CHAT_IDS": ALERT_CHAT,
            "WORKER_POLL_SECONDS": "1",
            "WORKER_INBOUND_POLL_SECONDS": "1",
            CLOCK_FILE_VARIABLE: str(self.clock.path),
            SENDS_FILE_VARIABLE: str(self.sends_file),
            **self.environment,
            **extra,
        }
        if self.provider_url is not None:
            environment[PROVIDER_URL_VARIABLE] = self.provider_url
        return environment

    def start_api(self, extra: Mapping[str, str] | None = None) -> str:
        """An API process on a free port, ready; its base URL."""

        port = free_port()
        log = (self.directory / f"api-{port}.log").open("wb")
        process = subprocess.Popen(
            [sys.executable, "-m", "tests.chaos.chaos_process", "api", str(port)],
            cwd=PROJECT_ROOT_DIRECTORY,
            env=self.process_environment(extra or {}),
            stdout=log,
            stderr=log,
        )
        self.processes.append(process)
        url = f"http://127.0.0.1:{port}"
        wait_until_ready(process, url)
        return url

    def start_worker(
        self, extra: Mapping[str, str] | None = None
    ) -> subprocess.Popen[bytes]:
        """A worker whose lanes take jobs (it pulsed by then)."""

        log_path = self.directory / f"worker-{len(self.processes)}.log"
        log = log_path.open("wb")
        process = subprocess.Popen(
            [sys.executable, "-m", "tests.chaos.chaos_process", "worker"],
            cwd=PROJECT_ROOT_DIRECTORY,
            env=self.process_environment(extra or {}),
            stdout=log,
            stderr=log,
        )
        self.processes.append(process)
        wait_for(partial(has_started, log_path), STARTUP_SECONDS, "the worker")
        return process

    def worker_log(self, process: subprocess.Popen[bytes]) -> str:
        index = self.processes.index(process)
        return read_log(self.directory / f"worker-{index}.log")

    def alerts(self, title: str) -> list[Sent]:
        """The team's messages about one alert (first line names its title)."""

        return headlines(self.sends_file, title)

    def query(
        self, statement: LiteralString, *parameters: object
    ) -> list[tuple[Any, ...]]:
        with self.postgres_server.admin_connection(self.database_name) as connection:
            return list(connection.execute(statement, parameters).fetchall())


def get_json(url: str, path: str) -> tuple[int, dict[str, Any]]:
    response = httpx.get(f"{url}{path}", timeout=10)
    try:
        body = cast(dict[str, Any], response.json())
    except ValueError:
        body = {}
    return response.status_code, body


def pipeline(url: str) -> tuple[int, dict[str, Any]]:
    return get_json(url, "/healthz/pipeline")


def component_levels(url: str) -> dict[str, str]:
    """GET /v1/platform/status: each component's level now."""

    status, body = get_json(url, "/v1/platform/status")
    assert status == 200, body
    return {str(item["component"]): str(item["level"]) for item in body["components"]}


@contextmanager
def chaos_world(
    postgres_server: ThrowawayPostgresServer,
    template_database: str,
    directory: Path,
    seed: Callable[[str], SeededRestaurant],
    provider_url: str | None = None,
) -> Generator[ChaosWorld]:
    """A fresh database seeded by `seed`; every process stopped afterwards."""

    database_name = postgres_server.create_database(template_name=template_database)
    try:
        restaurant = seed(str(postgres_server.app_database_url(database_name)))
        world = ChaosWorld(
            postgres_server=postgres_server,
            database_name=database_name,
            restaurant=restaurant,
            directory=directory,
            clock=ChaosClock(directory / "clock-offset"),
            provider_url=provider_url,
        )
        try:
            yield world
        finally:
            stop_processes(world.processes)
    finally:
        postgres_server.drop_database(database_name)
