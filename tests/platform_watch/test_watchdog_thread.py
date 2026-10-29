"""
The watchdog's thread in each API process: one look per interval, a failed
look does not end it, PIPELINE_WATCHDOG_SECONDS=0 turns it off, and the
process names itself as "<host>:<pid>".
"""

import logging
import os
import socket
import threading

import pytest

from app.containers.app import AppContainer
from app.gateways.http.pipeline_watchdog_thread import (
    PIPELINE_WATCHDOG_THREAD_NAME,
    start_pipeline_watchdog,
    stop_pipeline_watchdog,
    watch_until_stopped,
)
from app.schemas.constants.observability import PipelineState
from app.schemas.dto.pipeline_health import PipelineWatchReport, PipelineWatchTick
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.monitoring.constrained_integers import NotificationCount
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.monitoring.monitor_holder import this_process_holder
from tests.e2e.workshop_container import replace_provider

LOOKS: int = 3


class CountingOperator:
    """Fails its first look, alerts on its second, stops the loop on its third."""

    def __init__(self, stop_event: threading.Event) -> None:
        self.looks: int = 0
        self._stop_event: threading.Event = stop_event

    def operate(self, input_data: PipelineWatchTick) -> PipelineWatchReport:
        del input_data
        self.looks += 1
        if self.looks == 1:
            raise RuntimeError("The first look broke.")
        if self.looks == LOOKS:
            self._stop_event.set()
        return PipelineWatchReport(
            is_leader=True,
            pipeline=PipelineState.STALLED,
            sent_count=NotificationCount(2 if self.looks == 2 else 0),
        )


def test_the_loop_outlives_a_failed_look_until_stopped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stop_event = threading.Event()
    operator = CountingOperator(stop_event)

    with caplog.at_level(logging.WARNING):
        watch_until_stopped(operator, 0.001, stop_event)

    assert operator.looks == LOOKS
    assert "The pipeline watchdog's look failed" in caplog.text
    assert "sent 2 alert message(s); the pipeline is stalled" in caplog.text


def container_with(environment: dict[str, str]) -> AppContainer:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings(environment))
    return container


def test_zero_seconds_turns_the_watchdog_off() -> None:
    stop_event = threading.Event()

    thread = start_pipeline_watchdog(
        container_with({"PIPELINE_WATCHDOG_SECONDS": "0"}), stop_event
    )

    assert thread is None
    stop_pipeline_watchdog(thread)


def test_the_watchdog_thread_starts_and_stops_with_the_process() -> None:
    stop_event = threading.Event()

    thread = start_pipeline_watchdog(container_with({}), stop_event)
    assert thread is not None
    assert thread.name == PIPELINE_WATCHDOG_THREAD_NAME and thread.daemon
    stop_event.set()
    stop_pipeline_watchdog(thread)

    assert not thread.is_alive()


def test_the_watchdog_interval_comes_from_the_environment() -> None:
    default = assemble_app_settings({}).platform_alerts
    custom = assemble_app_settings({"PIPELINE_WATCHDOG_SECONDS": "15"}).platform_alerts

    assert int(default.watchdog_seconds) == 60
    assert int(custom.watchdog_seconds) == 15


@pytest.mark.parametrize("value", ["-1", "3601", "soon"])
def test_an_invalid_watchdog_interval_is_refused(value: str) -> None:
    with pytest.raises(ValidationFailedError, match="PIPELINE_WATCHDOG_SECONDS"):
        assemble_app_settings({"PIPELINE_WATCHDOG_SECONDS": value})


@pytest.mark.parametrize(
    ("host", "expected"),
    [("srv-workshop-api-7f9c", "srv-workshop-api-7f9c"), ("web 1_(eu)", "web-1-eu")],
)
def test_the_process_names_itself_by_host_and_pid(
    monkeypatch: pytest.MonkeyPatch, host: str, expected: str
) -> None:
    monkeypatch.setattr(socket, "gethostname", lambda: host)

    assert str(this_process_holder()) == f"{expected}:{os.getpid()}"


def test_a_host_without_a_usable_name_is_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "gethostname", lambda: "___")

    assert str(this_process_holder()) == f"host:{os.getpid()}"
