"""
The world of the two-process test: a restaurant published on the test
database (seeded in this process, on the real clock) and two API processes
(`two_process_api`) serving it from the same database.
"""

import os
import socket
import subprocess
import sys
import time
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
from typed_time_provider import Microseconds, WallClock

from app.containers.app import AppContainer
from tests.e2e.harness import bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import open_restaurant
from tests.e2e.workshop_container import replace_provider
from tests.storage.storage_testing import PROJECT_ROOT_DIRECTORY

STARTUP_SECONDS: float = 90.0
# The subprocesses get only what they need: no provider keys (no network),
# no platform bot to register at startup.
PROCESS_ENVIRONMENT_KEYS: tuple[str, ...] = ("APP_ENV", "ENCRYPTION_KEY")


@dataclass(frozen=True)
class SeededRestaurant:
    """A published restaurant: its id and its owner's bearer headers."""

    business_id: str
    headers: dict[str, str]

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"


def use_the_real_clock(container: AppContainer) -> None:
    """Seed on the wall clock the API processes use, not the e2e clock."""

    replace_provider(
        container.time_provider.microsecond_wall_clock,
        WallClock(preferred_time_unit_type=Microseconds),
    )


def seed_restaurant(database_url: str) -> SeededRestaurant:
    """Open the e2e restaurant (profile, table, trial, DPA, published)."""

    workshop = start_workshop(
        {**E2E_ENVIRONMENT, "DATABASE_URL": database_url},
        prepare=use_the_real_clock,
    )
    with workshop.client as client:
        restaurant = open_restaurant(workshop)
        connected = client.put(
            f"/v1/businesses/{restaurant.business_id}/channels/web",
            json={},
            headers=bearer(restaurant.owner_token),
        )
        assert connected.status_code == 200, connected.text

    return SeededRestaurant(
        business_id=restaurant.business_id,
        headers=bearer(restaurant.owner_token),
    )


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def process_environment(database_url: str) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        **{key: E2E_ENVIRONMENT[key] for key in PROCESS_ENVIRONMENT_KEYS},
        "DATABASE_URL": database_url,
        "LLM_PROVIDER": "scripted",
        "DB_POOL_SIZE": "12",
        "THREADPOOL_SIZE": "12",
    }


def wait_until_ready(process: subprocess.Popen[bytes], url: str) -> None:
    deadline = time.monotonic() + STARTUP_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"The API process at {url} exited early.")
        try:
            if httpx.get(f"{url}/healthz", timeout=2).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.2)

    raise AssertionError(f"The API process at {url} did not start.")


@contextmanager
def api_processes(
    database_url: str,
    call_log: Path,
    count: int = 2,
) -> Generator[list[str]]:
    """Start `count` API processes on the database; yield their base URLs."""

    environment: Mapping[str, str] = process_environment(database_url)
    ports: list[int] = [free_port() for _ in range(count)]
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tests.storage.two_process_api",
                str(port),
                str(call_log),
            ],
            cwd=PROJECT_ROOT_DIRECTORY,
            env=dict(environment),
        )
        for port in ports
    ]
    urls = [f"http://127.0.0.1:{port}" for port in ports]
    try:
        for process, url in zip(processes, urls, strict=True):
            wait_until_ready(process, url)
        yield urls
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def read_model_calls(call_log: Path) -> list[tuple[int, float, float]]:
    """(pid, started, ended) of every model call, in start order."""

    if not call_log.exists():
        return []

    calls: list[tuple[int, float, float]] = []
    for line in call_log.read_text(encoding="utf-8").splitlines():
        pid, started, ended = line.split()
        calls.append((int(pid), float(started), float(ended)))

    return sorted(calls, key=lambda call: call[1])
