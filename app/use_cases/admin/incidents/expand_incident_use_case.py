import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.incidents import IncidentRepoContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.incidents import IncidentScope
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.dto.incidents import IncidentExpansionPayload
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.businesses.constrained_integers import BusinessBatchSize
from app.schemas.typings.incidents.constrained_integers import (
    AffectedBusinessCount,
    NotifiedOwnerCount,
)
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.admin.incidents.incident_expansion import (
    EXPAND_INCIDENT_JOB,
    INCIDENT_BATCH_SIZE,
    expansion_payload,
    expansion_serial_key,
)
from app.use_cases.admin.incidents.incident_reach import IncidentReach
from app.use_cases.shared.storage_transaction import in_unit_of_work

LOGGER: logging.Logger = logging.getLogger(__name__)


class ExpandIncidentUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    The `expand_incident` job: an incident of every business
    (ALL_BUSINESSES) reaches the next keyset batch of businesses after its
    `expansion_cursor` (`BusinessRepoContract.list_batch`, in the order
    they were created): each gets the incident's audit entry and, for a
    data breach, its owners' notices through the outbox (`IncidentReach`).

    One transaction per batch holds the batch's audit entries, notices,
    the incident's new cursor and counts, and the job of the next batch
    (or `expanded_at` after the last), so a run that dies leaves the batch
    untold and its retry tells it once; runs of one incident never overlap
    (their serial key). Platform-wide: it reads every business.
    """

    def __init__(
        self,
        incident_repo: IncidentRepoContract,
        business_repo: BusinessRepoContract,
        reach: IncidentReach,
        job_queue: JobQueueFacilitatorContract,
        unit_of_work: StorageUnitOfWorkContract | None,
        wall_clock: WallClock[Microseconds],
        batch_size: BusinessBatchSize = INCIDENT_BATCH_SIZE,
    ) -> None:
        self._incident_repo: IncidentRepoContract = incident_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._reach: IncidentReach = reach
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._batch_size: BusinessBatchSize = batch_size

    def run(self, input_data: QueuedJobInput) -> JobReport:
        payload = IncidentExpansionPayload.model_validate_json(str(input_data.payload))
        with in_unit_of_work(self._unit_of_work):
            incident: IncidentDocument | None = self._incident_repo.get(
                payload.incident_id
            )
            if (
                incident is None
                or incident.scope is not IncidentScope.ALL_BUSINESSES
                or incident.expanded_at is not None
            ):
                LOGGER.info("Incident %s needs no walk", payload.incident_id)
                return JobReport()

            now: Microseconds = self._wall_clock.now_unix()
            batch: list[BusinessDocument] = self._business_repo.list_batch(
                incident.expansion_cursor, self._batch_size
            )
            notified: int = self._reach.reach(incident, batch, None, now)
            is_last: bool = len(batch) < int(self._batch_size)
            self._incident_repo.save(self._advanced(incident, batch, notified, now))
            if not is_last:
                self._job_queue.enqueue(
                    EXPAND_INCIDENT_JOB,
                    expansion_payload(incident.id),
                    None,
                    lane=JobLane.DEFAULT,
                    serial_key=expansion_serial_key(incident.id),
                )

        LOGGER.info(
            "Incident %s reached %d more businesses%s",
            incident.id,
            len(batch),
            "; the walk is done" if is_last else "",
        )
        return JobReport(processed_count=ProcessedItemCount(len(batch)))

    def _advanced(
        self,
        incident: IncidentDocument,
        batch: list[BusinessDocument],
        notified: int,
        now: Microseconds,
    ) -> IncidentDocument:
        reached: int = int(incident.reached_business_count or 0) + len(batch)
        owners: int = int(incident.notified_owner_count) + notified
        return incident.model_copy(
            update={
                "expansion_cursor": (
                    batch[-1].id if batch else incident.expansion_cursor
                ),
                "reached_business_count": AffectedBusinessCount(reached),
                "notified_owner_count": NotifiedOwnerCount(owners),
                "notified_at": (
                    now
                    if notified and incident.notified_at is None
                    else incident.notified_at
                ),
                "expanded_at": now if len(batch) < int(self._batch_size) else None,
                "updated_at": now,
            }
        )
