from app.contracts.repositories import ScheduleExceptionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.dto.resources import (
    ScheduleExceptionList,
    ScheduleExceptionListQuery,
)
from app.utilities.knowledge.resource_rules import to_schedule_exception_view


class ListScheduleExceptionsUseCase(
    UseCaseContract[ScheduleExceptionListQuery, ScheduleExceptionList]
):
    """
    List schedule exceptions by date.

    For one resource the list holds its own exceptions and the business-wide
    ones, because both change when that resource can be booked.
    """

    def __init__(self, schedule_exception_repo: ScheduleExceptionRepoContract) -> None:
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )

    def run(self, input_data: ScheduleExceptionListQuery) -> ScheduleExceptionList:
        exceptions: list[ScheduleExceptionDocument] = [
            exception
            for exception in self._schedule_exception_repo.list_by_business(
                input_data.business_id
            )
            if (
                input_data.resource_id is None
                or exception.resource_id is None
                or exception.resource_id == input_data.resource_id
            )
            and (input_data.from_date is None or exception.date >= input_data.from_date)
        ]
        exceptions.sort(
            key=lambda exception: (
                exception.date,
                "" if exception.resource_id is None else str(exception.resource_id),
            )
        )
        return ScheduleExceptionList(
            items=[to_schedule_exception_view(exception) for exception in exceptions]
        )
