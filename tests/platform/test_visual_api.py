"""
The visual tests' API (scripts/visual_api.py) starts its wall clocks at
VISUAL_CLOCK_START, so the demo data is seeded at the same moment in every
run: the clock stands there while the API starts and runs on with the
machine's clock once it has, the moment it runs on is logged for the tests
(web/e2e/support/apiClock.ts), and anything but development is refused.
"""

import logging
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from scripts.visual_api import (
    CLOCK_START_VARIABLE,
    ClockStartError,
    StartedClock,
    read_clock_start,
    runs_on_after_startup,
    start_wall_clocks,
)
from tests.e2e.workshop_container import replace_provider

START: int = 1_791_963_000 * 1_000_000_000
SECOND: int = 1_000_000_000


def machine_readings(*readings: int) -> Iterator[int]:
    yield from readings


def container_in(environment: str) -> AppContainer:
    container = AppContainer()
    replace_provider(
        container.config.app_settings,
        assemble_app_settings({"APP_ENV": environment, "ENCRYPTION_KEY": "x" * 32}),
    )
    return container


def test_the_clock_stands_at_the_start_until_it_runs_on(
    caplog: pytest.LogCaptureFixture,
) -> None:
    readings = machine_readings(5 * SECOND, 5 * SECOND + 250, 65 * SECOND)
    clock = StartedClock(START, machine=lambda: next(readings))

    with caplog.at_level(logging.WARNING):
        standing = [clock(), clock()]
        clock.run_on()
        clock.run_on()
        running = [clock(), clock()]

    assert standing == [START, START]
    assert running == [START + 250, START + 60 * SECOND]
    assert caplog.messages == [
        f"Visual clock: {START} ns at the machine's {5 * SECOND} ns"
    ]


def test_the_api_starts_at_the_start_and_runs_on_after() -> None:
    readings = machine_readings(7 * SECOND, 8 * SECOND)
    clock = StartedClock(START, machine=lambda: next(readings))
    seen: list[int] = []

    @asynccontextmanager
    async def startup(app: FastAPI) -> AsyncGenerator[None]:
        del app
        seen.append(clock())
        yield

    application = FastAPI(lifespan=startup)
    runs_on_after_startup(application, clock)
    with TestClient(application):
        seen.append(clock())

    assert seen == [START, START + SECOND]


def test_the_start_is_a_moment_with_its_offset() -> None:
    assert read_clock_start({CLOCK_START_VARIABLE: "2026-10-14T07:30:00+00:00"}) == (
        1_791_963_000 * SECOND
    )
    assert read_clock_start({CLOCK_START_VARIABLE: "2026-10-14T11:30:00+04:00"}) == (
        1_791_963_000 * SECOND
    )
    for value in ["", "tomorrow", "2026-10-14T07:30:00"]:
        with pytest.raises(ClockStartError):
            read_clock_start({CLOCK_START_VARIABLE: value})


def test_every_wall_clock_of_the_container_reads_the_started_clock() -> None:
    container = container_in("development")
    readings = machine_readings(0, SECOND, 2 * SECOND)
    clock = StartedClock(START, machine=lambda: next(readings))
    start_wall_clocks(container, clock)
    clock.run_on()

    time_provider = container.time_provider
    assert time_provider.microsecond_wall_clock().now_unix() == Microseconds(
        (START + SECOND) // 1000
    )
    assert int(time_provider.wall_clock().now_unix()) == START + 2 * SECOND


@pytest.mark.parametrize("environment", ["production", "test"])
def test_only_development_moves_its_clock(environment: str) -> None:
    with pytest.raises(ClockStartError, match="development"):
        start_wall_clocks(container_in(environment), StartedClock(START))
