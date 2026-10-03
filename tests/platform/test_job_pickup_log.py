"""
Every claimed job leaves one log line with `pickup_delay_ms`: how long it
waited between being due and a worker taking it (the pickup SLI of
docs/operations/capacity.md), as a field of its own in JSON and text logs.
"""

import json
import logging

import pytest
from typed_time_provider import Microseconds

from app.gateways.worker.queued_job_runner import log_pickup
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.platform.constrained_integers import JobAttemptCount
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.observability.log_formatting import (
    JsonLogFormatter,
    LogContextFilter,
    TextLogFormatter,
    log_fields,
)
from tests.platform.worker_fakes import (
    ControlledClock,
    FlakyQueuedOperator,
    build_worker,
)

PROCESS_INBOUND_MESSAGE: JobName = JobName("process_inbound_message")
MICROSECONDS_PER_MILLISECOND: int = 1_000


def make_record(**fields: int | str) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.tests",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Picked up a job",
        args=(),
        exc_info=None,
    )
    for name, value in log_fields(**fields).items():
        setattr(record, name, value)
    LogContextFilter().filter(record)
    return record


def test_json_lines_carry_the_measured_fields_as_numbers() -> None:
    line = json.loads(
        JsonLogFormatter().format(make_record(pickup_delay_ms=120, lane="inbound"))
    )

    assert line["pickup_delay_ms"] == 120
    assert line["lane"] == "inbound"
    assert line["message"] == "Picked up a job"


def test_text_lines_list_the_measured_fields_after_the_message() -> None:
    line = TextLogFormatter().format(make_record(pickup_delay_ms=7))

    assert line.endswith("Picked up a job [pickup_delay_ms=7]")


def test_a_line_without_fields_is_unchanged() -> None:
    record = logging.LogRecord("app.tests", logging.INFO, __file__, 1, "Hi", (), None)
    LogContextFilter().filter(record)

    assert "pickup_delay_ms" not in json.loads(JsonLogFormatter().format(record))


def test_the_pickup_line_names_the_job_and_its_wait(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = ControlledClock()
    job = QueuedJobDocument(
        name=PROCESS_INBOUND_MESSAGE,
        payload=JobPayloadJson("{}"),
        lane=JobLane.INBOUND,
        attempts=JobAttemptCount(1),
        run_at=clock.wall_clock().now_unix(),
        created_at=clock.wall_clock().now_unix(),
        updated_at=clock.wall_clock().now_unix(),
    )
    claimed_at = Microseconds(int(job.run_at) + 340 * MICROSECONDS_PER_MILLISECOND)

    with caplog.at_level(logging.INFO, logger="app.gateways.worker.queued_job_runner"):
        log_pickup(job, claimed_at)

    record = caplog.records[-1]
    assert record.getMessage() == (
        "Picked up job process_inbound_message on the inbound lane "
        "340 ms after it was due"
    )
    assert record.log_fields == {
        "pickup_delay_ms": 340,
        "lane": "inbound",
        "attempt": 1,
    }


def test_a_claim_by_the_worker_logs_the_pickup(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = ControlledClock()
    kit = build_worker(clock, [], {PROCESS_INBOUND_MESSAGE: FlakyQueuedOperator(0)})
    kit.queue.enqueue(
        PROCESS_INBOUND_MESSAGE,
        JobPayloadJson("{}"),
        business_id=None,
        lane=JobLane.INBOUND,
    )

    with caplog.at_level(logging.INFO, logger="app.gateways.worker.queued_job_runner"):
        kit.worker.run_queued_jobs()

    pickups = [
        record.log_fields for record in caplog.records if hasattr(record, "log_fields")
    ]
    assert pickups == [{"pickup_delay_ms": 0, "lane": "inbound", "attempt": 1}]
