from typed_time_provider import Microseconds, WallClock

from app.contracts.incidents import IncidentRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.dto.incidents import IncidentView, LinkIncidentAnnouncementCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.admin.incidents.incident_views import incident_view


class LinkIncidentAnnouncementUseCase(
    UseCaseContract[LinkIncidentAnnouncementCommand, IncidentView]
):
    """
    Names on an incident the status page announcement published with it
    (`RecordIncidentOrchestrator`), so the incident log links to what
    owners were told. Run right after both were stored by the same
    platform admin's request, which already checked the admin.

    Raises:
        NotFoundError: the incident does not exist.
    """

    def __init__(
        self,
        incident_repo: IncidentRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._incident_repo: IncidentRepoContract = incident_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: LinkIncidentAnnouncementCommand) -> IncidentView:
        incident: IncidentDocument | None = self._incident_repo.get(
            input_data.incident_id
        )
        if incident is None:
            raise NotFoundError("The incident does not exist.")

        linked: IncidentDocument = incident.model_copy(
            update={
                "announcement_id": input_data.announcement_id,
                "updated_at": self._wall_clock.now_unix(),
            }
        )
        self._incident_repo.save(linked)
        return incident_view(linked)
