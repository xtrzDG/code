"""
Worker lanes with real threads: a long autotest run never delays reminders
or customer messages, and one business runs one autotest at a time.
"""

import time

from app.contracts.jobs import QueuedJobRepoContract
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.lane_fakes import (
    GatedQueuedOperator,
    SignallingPeriodicOperator,
    running_worker,
    wait_until,
)
from tests.platform.worker_fakes import RUN_AUTOTESTS, ControlledClock, build_worker

PROCESS_INBOUND_MESSAGE: JobName = JobName("process_inbound_message")
SEND_BOOKING_REMINDERS: JobName = JobName("send_booking_reminders")
EMPTY_PAYLOAD: JobPayloadJson = JobPayloadJson("{}")


def autotest_key(business_id: BusinessId) -> JobSerialKey:
    return JobSerialKey(f"autotests:{business_id}")


def test_a_30_second_autotest_run_does_not_delay_a_due_reminder() -> None:
    clock = ControlledClock()
    reminders = SignallingPeriodicOperator()
    autotests = GatedQueuedOperator(max_seconds=30.0)
    inbound = GatedQueuedOperator(is_gated=False)
    kit = build_worker(
        clock,
        [
            PeriodicJobSpec(
                name=SEND_BOOKING_REMINDERS,
                interval_seconds=JobIntervalSeconds(15 * 60),
                operator=reminders,
            )
        ],
        {RUN_AUTOTESTS: autotests, PROCESS_INBOUND_MESSAGE: inbound},
        poll_seconds=1,
    )
    autotest_id = kit.queue.enqueue(
        RUN_AUTOTESTS, EMPTY_PAYLOAD, business_id=None, lane=JobLane.AUTOTESTS
    )

    with running_worker(kit.worker, on_exit=autotests.open_all):
        assert wait_until(lambda: autotest_id in autotests.running())
        assert wait_until(lambda: len(reminders.ticks) == 1)

        # The next reminder period comes while the autotest run still runs.
        clock.advance(15 * 60)
        due_at: float = time.monotonic()
        assert wait_until(lambda: len(reminders.ticks) == 2)
        assert reminders.tick_times[1] - due_at < 3.0  # one poll, not 30 s

        # A customer message on the inbound lane is not held up either.
        message_id = kit.queue.enqueue(
            PROCESS_INBOUND_MESSAGE,
            EMPTY_PAYLOAD,
            business_id=None,
            lane=JobLane.INBOUND,
        )
        assert wait_until(lambda: message_id in inbound.finished, timeout=3.0)
        assert autotests.running() == {autotest_id}

        autotests.open(autotest_id)
        assert wait_until(lambda: autotest_id in autotests.finished)
        assert wait_until(lambda: _status(kit.job_repo, autotest_id) == "done")


def test_one_autotest_run_per_business_at_a_time() -> None:
    clock = ControlledClock()
    autotests = GatedQueuedOperator()
    kit = build_worker(clock, [], {RUN_AUTOTESTS: autotests}, poll_seconds=1)
    salon, cafe = BusinessId(), BusinessId()
    salon_first, salon_second, cafe_run = (
        kit.queue.enqueue(
            RUN_AUTOTESTS,
            EMPTY_PAYLOAD,
            business_id=business_id,
            lane=JobLane.AUTOTESTS,
            serial_key=autotest_key(business_id),
        )
        for business_id in (salon, salon, cafe)
    )

    with running_worker(kit.worker, on_exit=autotests.open_all):
        # Two autotest threads: the salon's first run and the cafe's run;
        # the salon's second run waits for its first.
        assert wait_until(lambda: autotests.running() == {salon_first, cafe_run})
        time.sleep(0.3)
        assert salon_second not in autotests.started

        autotests.open(salon_first)
        assert wait_until(lambda: salon_second in autotests.running())
        assert autotests.started.index(salon_second) == 2

        autotests.open_all()
        assert wait_until(
            lambda: all(
                _status(kit.job_repo, job_id) == "done"
                for job_id in (salon_first, salon_second, cafe_run)
            )
        )


def test_stopping_the_worker_waits_for_running_jobs() -> None:
    clock = ControlledClock()
    slow = GatedQueuedOperator(max_seconds=0.5)
    kit = build_worker(clock, [], {RUN_AUTOTESTS: slow}, poll_seconds=1)
    job_id = kit.queue.enqueue(RUN_AUTOTESTS, EMPTY_PAYLOAD, business_id=None)

    with running_worker(kit.worker):
        assert wait_until(lambda: job_id in slow.running())

    # run_forever returned only after the job finished and was settled.
    assert job_id in slow.finished
    assert _status(kit.job_repo, job_id) == QueuedJobStatus.DONE.value


def _status(job_repo: QueuedJobRepoContract, job_id: QueuedJobId) -> str | None:
    job: QueuedJobDocument | None = job_repo.get(job_id)
    return None if job is None else job.status.value
