"""
The API of the cabinet's visual tests (web/e2e/visual, web/README.md
"Visual tests and the review gate"): the end-to-end suite's development API
whose wall clock stands at VISUAL_CLOCK_START while the API starts and runs
on from there once it has. The demo businesses (SEED_DEMO_DATA) are seeded
at startup relative to "now", so every run tells their story on the same
dates, minutes and seconds, whatever the real date:

    VISUAL_CLOCK_START=2026-10-21T07:30:00+00:00 APP_ENV=development \\
        uv run python -m scripts.visual_api --host 127.0.0.1 --port 8010

Only the wall clocks move (every "now" of the business modules and the
platform's own); the monotonic clock (timeouts, the worker's waits) stays
the machine's. The moment the clock starts running is logged with the
machine's time (CLOCK_LOG_LINE), so the tests know how far the API's clock
runs ahead (web/e2e/support/apiClock.ts: authenticator codes). It refuses
to start outside APP_ENV=development.
"""

import argparse
import logging
import os
import threading
import time
from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Protocol, cast

import uvicorn
from dependency_injector import providers
from dependency_injector.providers import Provider
from fastapi import FastAPI
from starlette.types import Lifespan
from typed_time_provider import Microseconds, Nanoseconds, WallClock

from app.containers.app import AppContainer
from app.main import create_application
from app.schemas.constants.environment import DeploymentEnvironment

CLOCK_START_VARIABLE: str = "VISUAL_CLOCK_START"
# Read by web/e2e/support/apiClock.ts: keep the wording.
CLOCK_LOG_LINE: str = "Visual clock: %d ns at the machine's %d ns"
MODULE: str = "scripts.visual_api"
NANOSECONDS_PER_SECOND: int = 1_000_000_000

LOGGER: logging.Logger = logging.getLogger(__name__)


class ClockStartError(ValueError):
    """VISUAL_CLOCK_START is missing or not a moment with its offset."""


class StartedClock:
    """
    Nanoseconds since the epoch: `start` until `run_on()` (the API has
    started: its demo data is seeded at exactly that moment), then on from
    there with the machine's clock.
    """

    def __init__(
        self,
        start_nanoseconds: int,
        machine: Callable[[], int] = time.time_ns,
    ) -> None:
        self._start_nanoseconds: int = start_nanoseconds
        self._machine: Callable[[], int] = machine
        self._offset: int | None = None
        self._lock: threading.Lock = threading.Lock()

    def run_on(self) -> None:
        with self._lock:
            if self._offset is None:
                reading: int = self._machine()
                self._offset = self._start_nanoseconds - reading
                LOGGER.warning(CLOCK_LOG_LINE, self._start_nanoseconds, reading)

    def __call__(self) -> int:
        with self._lock:
            if self._offset is None:
                return self._start_nanoseconds
            return self._machine() + self._offset


def runs_on_after_startup(application: FastAPI, clock: StartedClock) -> FastAPI:
    """The application starts (and seeds its demo data) at the clock's start."""

    startup: Lifespan[FastAPI] = application.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        async with startup(app):
            clock.run_on()
            yield

    application.router.lifespan_context = lifespan
    return application


def read_clock_start(environment: Mapping[str, str]) -> int:
    """VISUAL_CLOCK_START (ISO 8601 with its offset) in nanoseconds since the epoch."""

    value: str = environment.get(CLOCK_START_VARIABLE, "").strip()
    try:
        moment: datetime = datetime.fromisoformat(value)
    except ValueError as error:
        raise ClockStartError(
            f"{CLOCK_START_VARIABLE} must be a moment like 2026-10-21T07:30:00+00:00, "
            f"not {value!r}."
        ) from error
    if moment.utcoffset() is None:
        raise ClockStartError(f"{CLOCK_START_VARIABLE} needs its offset: {value!r}.")
    return round(moment.timestamp()) * NANOSECONDS_PER_SECOND


class OverridableProvider(Protocol):
    def override(self, provider: object) -> object: ...


def replace_provider[Provided](provider: Provider[Provided], value: Provided) -> None:
    cast(OverridableProvider, provider).override(providers.Object(value))


def start_wall_clocks(app_container: AppContainer, clock: StartedClock) -> AppContainer:
    """Every wall clock of the container reads `clock` (development only)."""

    environment = app_container.config.app_settings().environment
    if environment is not DeploymentEnvironment.DEVELOPMENT:
        raise ClockStartError(
            f"The visual tests' clock is for APP_ENV=development, not {environment}."
        )
    time_provider = app_container.time_provider
    replace_provider(
        time_provider.wall_clock,
        WallClock(Nanoseconds, unix_nanosecond_factory=clock),
    )
    replace_provider(
        time_provider.microsecond_wall_clock,
        WallClock(Microseconds, unix_nanosecond_factory=clock),
    )
    return app_container


def create_visual_application() -> FastAPI:
    """The uvicorn factory: the API with its wall clocks started."""

    clock = StartedClock(read_clock_start(os.environ))
    application = create_application(
        prepare=lambda app_container: start_wall_clocks(app_container, clock)
    )
    return runs_on_after_startup(application, clock)


def main(arguments: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    options = parser.parse_args(arguments)
    # Fails before uvicorn starts when the moment is missing or malformed.
    read_clock_start(os.environ)
    uvicorn.run(
        f"{MODULE}:{create_visual_application.__name__}",
        factory=True,
        host=options.host,
        port=options.port,
    )


if __name__ == "__main__":
    main()
