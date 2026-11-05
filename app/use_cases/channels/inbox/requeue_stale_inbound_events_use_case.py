import logging
from collections import defaultdict

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract, QueuedJobRepoContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.channels.inbox.claim_inbound_event_use_case import serial_key_of
from app.use_cases.channels.inbox.inbox_sweep_rules import (
    EVENT_JOBS,
    STALE_AFTER_SECONDS,
    job_payload,
    read_stale_events,
    seconds_before,
)
from app.use_cases.shared.inbox_queue import queue_inbound_job
from app.utilities.deliveries.inbound_claims import is_inbound_event_held

logger: logging.Logger = logging.getLogger(__name__)
UNFINISHED_STATUSES: tuple[InboundEventStatus, ...] = (
    InboundEventStatus.RECEIVED,
    InboundEventStatus.PROCESSING,
)


class RequeueStaleInboundEventsUseCase(UseCaseContract[JobTick, ProcessedItemCount]):
    """
    Find inbox events whose job was lost and queue it again: still RECEIVED
    or PROCESSING twice the processing lease after they arrived, not held
    by a processing whose lease runs, and with no job waiting or running
    for them (a job in its backoff still counts). Queuing one twice is
    harmless (the second job finds the event finished), so a sweep that
    runs again changes nothing. Returns how many were queued.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        job_repo: QueuedJobRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_repo: QueuedJobRepoContract = job_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> ProcessedItemCount:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        by_job: defaultdict[JobName, list[InboundEventDocument]] = defaultdict(list)
        for status in UNFINISHED_STATUSES:
            for event in read_stale_events(
                self._inbound_event_repo,
                status,
                seconds_before(now, STALE_AFTER_SECONDS),
            ):
                if not is_inbound_event_held(event, now):
                    by_job[EVENT_JOBS[event.kind]].append(event)

        requeued: int = 0
        for job_name, events in by_job.items():
            active: set[JobPayloadJson] = self._job_repo.list_active_payloads(
                job_name, [job_payload(event) for event in events]
            )
            for event in events:
                if job_payload(event) in active:
                    continue

                queue_inbound_job(
                    self._job_queue, event, job_name, serial_key_of(event)
                )
                requeued += 1

        if requeued:
            logger.warning(
                "The inbox sweep queued %d event(s) whose job was lost.", requeued
            )

        return ProcessedItemCount(requeued)
