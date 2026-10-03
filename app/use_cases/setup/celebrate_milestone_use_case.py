from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.setup_repositories import ActivationEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import ActivationEventDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.setup_progress import (
    ActivationMilestoneCheck,
    ActivationMilestoneView,
    CelebrateMilestoneCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError


class CelebrateMilestoneUseCase(
    UseCaseContract[CelebrateMilestoneCommand, ActivationMilestoneView]
):
    """
    The cabinet has shown a milestone's celebration (the first real
    customer, the first booking...): it is noted once, so no device shows
    it again. Milestones reached but not noticed yet are noticed first; a
    milestone the business has not reached is not found.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        record_activation_milestones: UseCaseContract[ActivationMilestoneCheck, None],
        activation_event_repo: ActivationEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._record_activation_milestones: UseCaseContract[
            ActivationMilestoneCheck, None
        ] = record_activation_milestones
        self._activation_event_repo: ActivationEventRepoContract = activation_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CelebrateMilestoneCommand) -> ActivationMilestoneView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        self._record_activation_milestones.run(
            ActivationMilestoneCheck(business_id=business.id)
        )
        event: ActivationEventDocument | None = (
            self._activation_event_repo.mark_celebrated(
                business.id, input_data.kind, self._wall_clock.now_unix()
            )
        )
        if event is None:
            raise NotFoundError(
                f"Milestone {input_data.kind.value} has not been reached yet."
            )

        return ActivationMilestoneView(
            kind=event.kind,
            occurred_at=event.occurred_at,
            celebrated_at=event.celebrated_at,
        )
