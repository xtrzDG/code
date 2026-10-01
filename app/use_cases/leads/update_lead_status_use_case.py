from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import LeadRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.bookings import LeadDocument
from app.schemas.dto.bookings import LeadView
from app.schemas.dto.operations import UpdateLeadStatusCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.leads.lead_views import build_lead_view


class UpdateLeadStatusUseCase(UseCaseContract[UpdateLeadStatusCommand, LeadView]):
    """Staff moves a lead between NEW, IN_PROGRESS, WON and LOST (any order)."""

    def __init__(
        self,
        lead_repo: LeadRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._lead_repo: LeadRepoContract = lead_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateLeadStatusCommand) -> LeadView:
        lead: LeadDocument | None = self._lead_repo.get(
            input_data.business_id, input_data.lead_id
        )
        if lead is None:
            raise NotFoundError(f"Lead {input_data.lead_id} was not found.")

        if lead.status is not input_data.status:
            lead.status = input_data.status
            lead.updated_at = self._wall_clock.now_unix()
            self._lead_repo.save(lead)

        return build_lead_view(lead)
