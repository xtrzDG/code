import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import (
    BusyTimeSyncFacilitatorContract,
    ResourceCalendarLinkRepoContract,
)
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.calendar_sync.busy_windows import BACKGROUND_READ_SECONDS

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
# Resources one run looks at; the rest stay due for the next run.
SYNC_LIMIT: DocumentQueryLimit = DocumentQueryLimit(200)
# A run stops starting reads after this long: it never overlaps the next.
RUN_BUDGET_SECONDS: int = 4 * 60


class SyncDueCalendarsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job (every five minutes, across businesses): the resources
    whose calendars are due, oldest first, read again (each source within
    10 s); each is due again a sync period later. A resource that is gone
    is not read again. One resource's failure never stops the others.
    """

    def __init__(
        self,
        link_repo: ResourceCalendarLinkRepoContract,
        resource_repo: ResourceRepoContract,
        busy_time_sync: BusyTimeSyncFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._link_repo: ResourceCalendarLinkRepoContract = link_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._busy_time_sync: BusyTimeSyncFacilitatorContract = busy_time_sync
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        started: int = int(self._wall_clock.now_unix())
        deadline: int = started + RUN_BUDGET_SECONDS * MICROSECONDS_PER_SECOND
        synced: int = 0
        for link in self._link_repo.list_due(Microseconds(started), SYNC_LIMIT):
            if int(self._wall_clock.now_unix()) >= deadline:
                break
            if self._sync(link):
                synced += 1

        return JobReport(processed_count=ProcessedItemCount(synced))

    def _sync(self, link: ResourceCalendarLinkDocument) -> bool:
        resource: ResourceDocument | None = self._resource_repo.get(
            link.business_id, link.resource_id
        )
        if resource is None:
            self._link_repo.update(link.business_id, link.resource_id, stop_reading)
            return False

        try:
            self._busy_time_sync.sync_resource(resource, BACKGROUND_READ_SECONDS)
        except Exception:  # noqa: BLE001 - one resource never stops the run
            LOGGER.exception("Syncing the calendars of %s failed.", resource.id)
            return False

        return True


def stop_reading(link: ResourceCalendarLinkDocument) -> ResourceCalendarLinkDocument:
    """The settings of a resource that is gone: never due again."""

    link.next_sync_at = None
    return link
