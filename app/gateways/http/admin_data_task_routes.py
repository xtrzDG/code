"""Platform admin: the post-deploy data tasks (the system page's card)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.data_tasks import (
    DataTasksQuery,
    DataTasksView,
    RetryDataTaskCommand,
    RetryDataTaskResult,
)
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.users.prefixed_id import UserId

type GetDataTasksOperator = OperatorContract[DataTasksQuery, DataTasksView]
type RetryDataTaskOperator = OperatorContract[RetryDataTaskCommand, RetryDataTaskResult]


def build_admin_data_task_router(
    get_data_tasks_operator: GetDataTasksOperator,
    retry_data_task_operator: RetryDataTaskOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a platform admin; others get 403):
        GET  /v1/admin/system/data-tasks              every post-deploy data
                                                      task, its progress and
                                                      whether the release
                                                      overlap is over
        POST /v1/admin/system/data-tasks/{key}/retry  walk a FAILED task
                                                      again (audited)

    A task that is not failed is answered with 409, an unknown key with 404.
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get("/v1/admin/system/data-tasks")
    def get_data_tasks(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> DataTasksView:
        return get_data_tasks_operator.operate(DataTasksQuery(user_id=user_id))

    @router.post("/v1/admin/system/data-tasks/{task_key}/retry")
    def retry_data_task(
        request: Request,
        task_key: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> RetryDataTaskResult:
        return retry_data_task_operator.operate(
            RetryDataTaskCommand(
                user_id=user_id,
                key=parse_path_identifier(task_key, DataTaskKey, "Data task"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
