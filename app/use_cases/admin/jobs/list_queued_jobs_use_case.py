from typed_time_provider import Microseconds

from app.contracts.jobs import QueuedJobRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_jobs import AdminJobsQuery, QueuedJobPage
from app.schemas.dto.job_queue import QueuedJobPageQuery, QueuedJobPosition
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.jobs.queued_job_views import build_queued_job_view
from app.utilities.paging.cursor_paging import (
    INVALID_CURSOR_MESSAGE,
    decode_page_cursor,
    encode_page_cursor,
)


class ListQueuedJobsUseCase(UseCaseContract[AdminJobsQuery, QueuedJobPage]):
    """
    The background job queue for the platform admin, the most recently
    changed job first: the dead letters (`status=dead`), what waits, runs
    or was discarded, optionally of one job name. Paged in the database
    (keyset on the last change), never by reading the whole queue.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[UserId, UserDocument],
        job_repo: QueuedJobRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[UserId, UserDocument] = (
            authorize_platform_admin
        )
        self._job_repo: QueuedJobRepoContract = job_repo

    def run(self, input_data: AdminJobsQuery) -> QueuedJobPage:
        self._authorize_platform_admin.run(input_data.user_id)
        jobs: list[QueuedJobDocument] = self._job_repo.list_page(
            QueuedJobPageQuery(
                status=input_data.status,
                name=input_data.name,
                after=decode_position(input_data.page.cursor),
                page_size=input_data.page.size,
            )
        )
        page_size: int = int(input_data.page.size)
        items: list[QueuedJobDocument] = jobs[:page_size]
        next_cursor: PageCursor | None = (
            encode_page_cursor(int(items[-1].updated_at), str(items[-1].id))
            if len(jobs) > page_size and items
            else None
        )
        return QueuedJobPage(
            items=[build_queued_job_view(job) for job in items],
            next_cursor=next_cursor,
        )


def decode_position(cursor: PageCursor | None) -> QueuedJobPosition | None:
    """Where the previous page ended; ValidationFailedError for a broken cursor."""

    if cursor is None:
        return None

    updated_at, job_id = decode_page_cursor(cursor)
    try:
        return QueuedJobPosition(
            updated_at=Microseconds(updated_at),
            job_id=QueuedJobId(job_id),
        )
    except ValueError as error:
        raise ValidationFailedError(INVALID_CURSOR_MESSAGE) from error
