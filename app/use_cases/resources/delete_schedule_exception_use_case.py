from app.contracts.repositories import ScheduleExceptionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.resources import (
    DeleteScheduleExceptionCommand,
    ScheduleExceptionDeletion,
)
from app.schemas.exceptions.application_errors import NotFoundError


class DeleteScheduleExceptionUseCase(
    UseCaseContract[DeleteScheduleExceptionCommand, ScheduleExceptionDeletion]
):
    """Delete a schedule exception; one of another business is reported missing."""

    def __init__(self, schedule_exception_repo: ScheduleExceptionRepoContract) -> None:
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )

    def run(
        self,
        input_data: DeleteScheduleExceptionCommand,
    ) -> ScheduleExceptionDeletion:
        is_known: bool = any(
            exception.id == input_data.exception_id
            for exception in self._schedule_exception_repo.list_by_business(
                input_data.business_id
            )
        )
        if not is_known:
            raise NotFoundError(
                f"Schedule exception {input_data.exception_id} was not found."
            )

        self._schedule_exception_repo.delete(
            input_data.business_id,
            input_data.exception_id,
        )
        return ScheduleExceptionDeletion(id=input_data.exception_id)
