"""Closing a business (owners), cancelling the closure, and where it stands."""

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
from app.schemas.dto.business_closures.closure_views import (
    BusinessClosureView,
    CancelBusinessClosureCommand,
    CloseBusinessCommand,
    CloseBusinessRequest,
)
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_close_business_body = build_json_body_dependency(CloseBusinessRequest)


def build_business_closure_router(
    get_business_closure_operator: OperatorContract[BusinessQuery, BusinessClosureView],
    close_business_operator: OperatorContract[
        CloseBusinessCommand, BusinessClosureView
    ],
    cancel_business_closure_operator: OperatorContract[
        CancelBusinessClosureCommand, None
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        GET    /v1/businesses/{business_id}/closure  where the business stands
               on its way out: active, pending deletion (until when, why, by
               whom, whether this person may cancel) or deleting (members)
        POST   /v1/businesses/{business_id}/closure  close the business: the
               assistant pauses, the channels go off, charges stop and the data
               is deleted in 30 days (owner, step-up, the business's name typed
               to confirm; audited, owners told)
        DELETE /v1/businesses/{business_id}/closure  cancel the closure before
               the deletion begins (owner, step-up; 204)
    """

    router = APIRouter(tags=["businesses"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/closure")
    def get_business_closure(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> BusinessClosureView:
        return get_business_closure_operator.operate(
            BusinessQuery(user_id=user_id, business_id=parse_business_id(business_id))
        )

    @router.post(
        "/v1/businesses/{business_id}/closure",
        openapi_extra=describe_json_body(CloseBusinessRequest),
    )
    def close_business(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CloseBusinessRequest, Depends(read_close_business_body)],
    ) -> BusinessClosureView:
        return close_business_operator.operate(
            CloseBusinessCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                confirmation_name=body.confirmation_name,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(
        "/v1/businesses/{business_id}/closure",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def cancel_business_closure(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        cancel_business_closure_operator.operate(
            CancelBusinessClosureCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router


def parse_business_id(raw_business_id: str) -> BusinessId:
    return parse_path_identifier(raw_business_id, BusinessId, "Business")
