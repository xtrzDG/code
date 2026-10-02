"""Platform admin: the background job queue and its dead letters (API only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.dto.admin_jobs import (
    AdminJobActionResult,
    AdminJobCommand,
    AdminJobsQuery,
    QueuedJobPage,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.users.prefixed_id import UserId

type ListQueuedJobsOperator = OperatorContract[AdminJobsQuery, QueuedJobPage]
type QueuedJobActionOperator = OperatorContract[AdminJobCommand, AdminJobActionResult]


def build_admin_jobs_router(
    list_queued_jobs_operator: ListQueuedJobsOperator,
    retry_queued_job_operator: QueuedJobActionOperator,
    discard_queued_job_operator: QueuedJobActionOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a platform admin; others get 403):
        GET  /v1/admin/jobs                      queued jobs, newest change
             ?limit=&cursor=&status=&name=       first (status=dead: the
                                                 dead letters)
        POST /v1/admin/jobs/{job_id}/retry       run a dead or discarded job
                                                 again (audited)
        POST /v1/admin/jobs/{job_id}/discard     drop a dead or waiting job
                                                 (audited)

    A job that is running, done, or in the wrong state for the action is
    answered with 409; payloads are never returned.
    """

    router = APIRouter(tags=["admin"])

    @router.get("/v1/admin/jobs")
    def list_queued_jobs(
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
        status: str | None = None,
        name: str | None = None,
    ) -> QueuedJobPage:
        return list_queued_jobs_operator.operate(
            AdminJobsQuery(
                user_id=user_id,
                page=parse_page_request(limit, cursor),
                status=parse_optional(status, QueuedJobStatus, "status"),
                name=parse_optional(
                    None if name is None else name.strip(), JobName, "name"
                ),
            )
        )

    @router.post("/v1/admin/jobs/{job_id}/retry")
    def retry_queued_job(
        request: Request,
        job_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AdminJobActionResult:
        return retry_queued_job_operator.operate(
            AdminJobCommand(
                user_id=user_id,
                job_id=parse_path_identifier(job_id, QueuedJobId, "Job"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post("/v1/admin/jobs/{job_id}/discard")
    def discard_queued_job(
        request: Request,
        job_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AdminJobActionResult:
        return discard_queued_job_operator.operate(
            AdminJobCommand(
                user_id=user_id,
                job_id=parse_path_identifier(job_id, QueuedJobId, "Job"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
