from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import (
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.dto.resources import (
    CreateScheduleExceptionCommand,
    ScheduleExceptionView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.utilities.knowledge.resource_rules import (
    build_schedule_exception,
    to_schedule_exception_view,
)


class CreateScheduleExceptionUseCase(
    UseCaseContract[CreateScheduleExceptionCommand, ScheduleExceptionView]
):
    """
    Add a holiday, closed day or special-hours day for the business or one
    resource (concept schedule_exceptions).

    The date is a calendar date in the business time zone and must not be
    past there. A resource of another business is reported as missing.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateScheduleExceptionCommand) -> ScheduleExceptionView:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        resource_id: ResourceId | None = input_data.exception.resource_id
        if (
            resource_id is not None
            and self._resource_repo.get(business.id, resource_id) is None
        ):
            raise NotFoundError(f"Resource {resource_id} was not found.")

        exception: ScheduleExceptionDocument = build_schedule_exception(
            business=business,
            exception_input=input_data.exception,
            existing_exceptions=self._schedule_exception_repo.list_by_business(
                business.id
            ),
            now=self._wall_clock.now_unix(),
        )
        self._schedule_exception_repo.save(exception)
        return to_schedule_exception_view(exception)
