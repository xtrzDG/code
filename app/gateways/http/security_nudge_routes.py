"""The reminder to protect customers' data with a second factor (owners)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.setup_routes import parse_business_id
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.security_nudges import (
    DismissSecurityNudgeCommand,
    SecurityNudgeQuery,
    SecurityNudgeView,
)
from app.schemas.typings.users.prefixed_id import UserId

SECURITY_NUDGE_PATH: str = "/v1/businesses/{business_id}/security-nudge"


def build_security_nudge_router(
    current_user: CurrentUserDependency,
    get_security_nudge_operator: OperatorContract[
        SecurityNudgeQuery, SecurityNudgeView
    ],
    dismiss_security_nudge_operator: OperatorContract[
        DismissSecurityNudgeCommand, SecurityNudgeView
    ],
) -> APIRouter:
    """
    Routes (bearer token):
        GET /v1/businesses/{business_id}/security-nudge
            whether the banner "Protect your customers' data: turn on a
            second factor" shows (owners and staff may ask; owners see it)
        PUT /v1/businesses/{business_id}/security-nudge/dismissal
            put it away (owners); it comes back once the team grows past
            one person
    """

    router: APIRouter = APIRouter(tags=["setup"], responses=standard_error_responses())

    @router.get(SECURITY_NUDGE_PATH)
    def get_security_nudge(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> SecurityNudgeView:
        return get_security_nudge_operator.operate(
            SecurityNudgeQuery(
                user_id=user_id, business_id=parse_business_id(business_id)
            )
        )

    @router.put(SECURITY_NUDGE_PATH + "/dismissal")
    def dismiss_security_nudge(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> SecurityNudgeView:
        return dismiss_security_nudge_operator.operate(
            DismissSecurityNudgeCommand(
                user_id=user_id, business_id=parse_business_id(business_id)
            )
        )

    return router
