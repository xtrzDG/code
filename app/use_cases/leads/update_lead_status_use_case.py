from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.booking_repositories import LeadRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import LeadDocument
from app.schemas.dto.bookings import LeadView
from app.schemas.dto.inbox.assignment import OpenRequestRefresh, OpenRequestState
from app.schemas.dto.operations.leads import UpdateLeadStatusCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.shared.lead_views import build_lead_view
from app.use_cases.shared.request_tracking import track_request


class UpdateLeadStatusUseCase(UseCaseContract[UpdateLeadStatusCommand, LeadView]):
    """
    Staff moves a lead between NEW, IN_PROGRESS, WON and LOST (any order).
    Its conversation stays in the team inbox's "Requests" view while one of
    its requests is new or in progress.
    """

    def __init__(
        self,
        lead_repo: LeadRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        refresh_open_request: UseCaseContract[OpenRequestRefresh, OpenRequestState],
    ) -> None:
        self._lead_repo: LeadRepoContract = lead_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._refresh_open_request: UseCaseContract[
            OpenRequestRefresh, OpenRequestState
        ] = refresh_open_request

    def run(self, input_data: UpdateLeadStatusCommand) -> LeadView:
        now: Microseconds = self._wall_clock.now_unix()
        # One atomic step, so a deposit written meanwhile is never lost.
        changed: LeadDocument | None = self._lead_repo.update(
            input_data.business_id,
            input_data.lead_id,
            lambda stored: with_status(stored, input_data.status, now),
        )
        if changed is None:
            unchanged: LeadDocument | None = self._lead_repo.get(
                input_data.business_id, input_data.lead_id
            )
            if unchanged is None:
                raise NotFoundError(f"Lead {input_data.lead_id} was not found.")

            return build_lead_view(unchanged)

        self._live_events.publish(
            changed.business_id,
            LiveEventKind.LEAD_CHANGED,
            (changed.id,),
            is_sandbox=changed.is_sandbox,
        )
        track_request(changed, self._refresh_open_request)
        return build_lead_view(changed)


def with_status(
    lead: LeadDocument, status: LeadStatus, now: Microseconds
) -> LeadDocument | None:
    """The lead in its new status; None when it already has it."""

    if lead.status is status:
        return None

    lead.status = status
    lead.updated_at = now
    return lead
