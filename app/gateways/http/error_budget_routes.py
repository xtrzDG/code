"""Platform admin: the error budgets of the SLOs (docs/operations/slo.md)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.service_levels import ErrorBudgetQuery, ErrorBudgetView
from app.schemas.typings.users.prefixed_id import UserId

type GetErrorBudgetOperator = OperatorContract[ErrorBudgetQuery, ErrorBudgetView]


def build_error_budget_router(
    get_error_budget_operator: GetErrorBudgetOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a platform admin; others get 403):
        GET  /v1/admin/system/error-budget   the SLOs over the hourly rows
             of the last 28 days: each ratio objective's events, budget
             left and last hour's burn rate, and the answer latency p95
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get("/v1/admin/system/error-budget")
    def get_error_budget(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ErrorBudgetView:
        return get_error_budget_operator.operate(ErrorBudgetQuery(user_id=user_id))

    return router
