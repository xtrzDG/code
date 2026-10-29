import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.service_levels import (
    ServiceLevelHourRepoContract,
    ServiceLevelSlotRepoContract,
    ServiceLevelSourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.service_levels import (
    ServiceLevelHourDocument,
    ServiceLevelSlotDocument,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.service_levels import LatencyBucketTally, ServiceLevelTally
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.client_health.reply_speed import REPLY_LATENCY_BUCKET_STARTS
from app.utilities.observability.service_levels import (
    ANSWER_DEADLINE_MICROSECONDS,
    HOUR_MICROSECONDS,
    SLOT_MICROSECONDS,
    answer_p95,
    hour_start_of,
    slot_start_of,
    sum_slots,
    tally_answers,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
DAY_MICROSECONDS: int = 24 * HOUR_MICROSECONDS
# A slot's customer messages are judged once the last of them had its 60 s
# and the worker that answers it a little more to store the outcome.
SLOT_SETTLE_MICROSECONDS: int = ANSWER_DEADLINE_MICROSECONDS + 60 * 1_000_000
# An hour is summed once its last slot is judged and every API process
# flushed its counts (every 15 s).
HOUR_SETTLE_MICROSECONDS: int = 10 * 60 * 1_000_000
# After a pause the job catches up at most one day; older gaps stay gaps.
CATCH_UP_MICROSECONDS: int = DAY_MICROSECONDS
SLOT_RETENTION_MICROSECONDS: int = 35 * DAY_MICROSECONDS
HOUR_RETENTION_MICROSECONDS: int = 90 * DAY_MICROSECONDS
EVENTS_PER_SLOT: DocumentQueryLimit = DocumentQueryLimit(10_000)
BUCKET_STARTS: tuple[ReplyLatencyMilliseconds, ...] = tuple(
    ReplyLatencyMilliseconds(start) for start in REPLY_LATENCY_BUCKET_STARTS
)


class RecordServiceLevelsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The `record_sli` periodic job (every five minutes, once per period
    across workers; docs/operations/slo.md):

    1. every five-minute slot whose customer messages all had their 60 s is
       judged: the messages of the slot, and those answered or handed off
       within 60 s of arriving;
    2. every hour that is over (and settled) becomes one row: those counts,
       the p95 of the assistant replies' measured wait (`reply_latency_ms`)
       and the API's requests and server errors the API processes added to
       the slots;
    3. slots older than 35 days and rows older than 90 days are removed.

    The job resumes after the newest stored slot and row (a day at most;
    the first run starts with the previous hour), and a rerun of a slot or
    an hour writes the same row again. The
    report counts the slots and hours written.
    """

    def __init__(
        self,
        slot_repo: ServiceLevelSlotRepoContract,
        hour_repo: ServiceLevelHourRepoContract,
        source_repo: ServiceLevelSourceRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._slot_repo: ServiceLevelSlotRepoContract = slot_repo
        self._hour_repo: ServiceLevelHourRepoContract = hour_repo
        self._source_repo: ServiceLevelSourceRepoContract = source_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: int = int(self._wall_clock.now_unix())
        slots: int = self._judge_slots(now)
        hours: int = self._sum_hours(now)
        self._slot_repo.delete_before(Microseconds(now - SLOT_RETENTION_MICROSECONDS))
        self._hour_repo.delete_before(Microseconds(now - HOUR_RETENTION_MICROSECONDS))
        return JobReport(processed_count=ProcessedItemCount(slots + hours))

    def _judge_slots(self, now: int) -> int:
        judged_until: int = int(slot_start_of(now - SLOT_SETTLE_MICROSECONDS))
        latest: ServiceLevelSlotDocument | None = self._slot_repo.find_latest(
            ServiceLevelSeries.INBOUND_ANSWERED
        )
        # The first run starts with the previous hour, so its row is whole.
        first: int = (
            int(hour_start_of(judged_until)) - HOUR_MICROSECONDS
            if latest is None
            else int(latest.slot_start) + SLOT_MICROSECONDS
        )
        starts = range(
            max(first, judged_until - CATCH_UP_MICROSECONDS),
            judged_until,
            SLOT_MICROSECONDS,
        )
        for start in starts:
            self._judge_slot(Microseconds(start))
        return len(starts)

    def _judge_slot(self, start: Microseconds) -> None:
        events: list[InboundEventDocument] = self._source_repo.list_inbound_events(
            start, Microseconds(int(start) + SLOT_MICROSECONDS), EVENTS_PER_SLOT
        )
        if len(events) >= int(EVENTS_PER_SLOT):
            LOGGER.warning(
                "Service level slot capped at %s inbox events", int(EVENTS_PER_SLOT)
            )
        total, good = tally_answers(events)
        self._slot_repo.save(
            ServiceLevelSlotDocument(
                series=ServiceLevelSeries.INBOUND_ANSWERED,
                slot_start=start,
                total=total,
                good=good,
            )
        )

    def _sum_hours(self, now: int) -> int:
        summed_until: int = int(hour_start_of(now - HOUR_SETTLE_MICROSECONDS))
        latest: ServiceLevelHourDocument | None = self._hour_repo.find_latest()
        first: int = (
            summed_until - HOUR_MICROSECONDS
            if latest is None
            else int(latest.hour_start) + HOUR_MICROSECONDS
        )
        starts = range(
            max(first, summed_until - CATCH_UP_MICROSECONDS),
            summed_until,
            HOUR_MICROSECONDS,
        )
        for start in starts:
            self._hour_repo.save(self._hour_row(Microseconds(start)))
        return len(starts)

    def _hour_row(self, start: Microseconds) -> ServiceLevelHourDocument:
        end: Microseconds = Microseconds(int(start) + HOUR_MICROSECONDS)
        inbound: ServiceLevelTally = self._tally(
            ServiceLevelSeries.INBOUND_ANSWERED, start, end
        )
        api: ServiceLevelTally = self._tally(
            ServiceLevelSeries.API_AVAILABILITY, start, end
        )
        latencies: list[LatencyBucketTally] = self._source_repo.count_reply_latencies(
            start, end, BUCKET_STARTS
        )
        return ServiceLevelHourDocument(
            hour_start=start,
            inbound_messages=inbound.total,
            inbound_in_time=inbound.good,
            measured_replies=ServiceLevelEventCount(
                sum(int(tally.count) for tally in latencies)
            ),
            reply_p95_ms=answer_p95(latencies),
            api_requests=api.total,
            api_server_errors=ServiceLevelEventCount(int(api.total) - int(api.good)),
        )

    def _tally(
        self, series: ServiceLevelSeries, start: Microseconds, end: Microseconds
    ) -> ServiceLevelTally:
        return sum_slots(series, self._slot_repo.list_window(series, start, end))
