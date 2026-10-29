"""Platform support's access to a business, as its team sees and controls it."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.support_access import (
    EndSupportAccessCommand,
    SupportAccessQuery,
    SupportAccessView,
    UpdateSupportWriteAccessCommand,
    UpdateSupportWriteAccessRequest,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_write_access_body = build_json_body_dependency(UpdateSupportWriteAccessRequest)


def build_support_access_router(
    get_support_access_operator: OperatorContract[
        SupportAccessQuery, SupportAccessView
    ],
    update_support_write_access_operator: OperatorContract[
        UpdateSupportWriteAccessCommand, SupportAccessView
    ],
    end_support_access_operator: OperatorContract[EndSupportAccessCommand, None],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        GET    /v1/businesses/{business_id}/support-access  who of platform
               support looks into the cabinet now, why and until when, and
               whether the owner allows changes (team; support itself)
        PUT    /v1/businesses/{business_id}/support-access/write-access
               {is_allowed, hours}: allow changes for some hours or stop
               (owner; step-up to allow; audited)
        DELETE /v1/businesses/{business_id}/support-access  end support's
               access now (owner; 204; audited)
    """

    router = APIRouter(tags=["businesses"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/support-access")
    def get_support_access(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> SupportAccessView:
        return get_support_access_operator.operate(
            SupportAccessQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/support-access/write-access",
        openapi_extra=describe_json_body(UpdateSupportWriteAccessRequest),
    )
    def update_support_write_access(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            UpdateSupportWriteAccessRequest, Depends(read_write_access_body)
        ],
    ) -> SupportAccessView:
        return update_support_write_access_operator.operate(
            UpdateSupportWriteAccessCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                is_allowed=body.is_allowed,
                hours=body.hours,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(
        "/v1/businesses/{business_id}/support-access",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def end_support_access(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        end_support_access_operator.operate(
            EndSupportAccessCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
