"""The admin's spend tile and a client's own daily spend limits."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.spend_guard import (
    AdminSpendQuery,
    BusinessSpendLimitsCommand,
    BusinessSpendLimitsRequest,
    BusinessSpendLimitsView,
    PlatformSpendView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_spend_limits_body = build_json_body_dependency(BusinessSpendLimitsRequest)


def build_admin_spend_router(
    *,
    current_user: CurrentUserDependency,
    get_platform_spend: OperatorContract[AdminSpendQuery, PlatformSpendView],
    set_business_spend_limits: OperatorContract[
        BusinessSpendLimitsCommand, BusinessSpendLimitsView
    ],
) -> APIRouter:
    """
    Routes (Bearer auth; platform admins):
        GET /v1/admin/spend
            the platform's provider spend today (UTC) by provider, the 7
            days before's daily mean, the daily budget used, and the
            businesses past one of their limits in the last day
        PUT /v1/admin/clients/{business_id}/spend-limits
            a client's own daily soft and hard limits in micro-USD (null:
            the plan's default); audited on the client's log
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get("/v1/admin/spend")
    def get_admin_spend(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PlatformSpendView:
        return get_platform_spend.operate(AdminSpendQuery(user_id=user_id))

    @router.put(
        "/v1/admin/clients/{business_id}/spend-limits",
        openapi_extra=describe_json_body(BusinessSpendLimitsRequest),
    )
    def set_client_spend_limits(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[BusinessSpendLimitsRequest, Depends(read_spend_limits_body)],
    ) -> BusinessSpendLimitsView:
        return set_business_spend_limits.operate(
            BusinessSpendLimitsCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Client"),
                request=body,
            )
        )

    return router
