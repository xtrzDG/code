"""A business's two-factor requirement for its team."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.mfa import (
    BusinessSecurityView,
    UpdateBusinessSecurityCommand,
    UpdateBusinessSecurityRequest,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_update_body = build_json_body_dependency(UpdateBusinessSecurityRequest)


def build_business_security_router(
    get_business_security_operator: OperatorContract[
        BusinessQuery, BusinessSecurityView
    ],
    update_business_security_operator: OperatorContract[
        UpdateBusinessSecurityCommand, BusinessSecurityView
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        GET /v1/businesses/{business_id}/security  whether the team must sign
            in with two factors, members without an authenticator (members)
        PUT /v1/businesses/{business_id}/security  turn it on or off (owner,
            step-up; on needs the owner's own two-factor session; audited)
    """

    router = APIRouter(tags=["businesses"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/security")
    def get_business_security(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> BusinessSecurityView:
        return get_business_security_operator.operate(
            BusinessQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/security",
        openapi_extra=describe_json_body(UpdateBusinessSecurityRequest),
    )
    def update_business_security(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[UpdateBusinessSecurityRequest, Depends(read_update_body)],
    ) -> BusinessSecurityView:
        return update_business_security_operator.operate(
            UpdateBusinessSecurityCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                require_mfa_for_members=body.require_mfa_for_members,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
