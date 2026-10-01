"""Businesses (tenants), their settings and team."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.businesses import (
    BusinessQuery,
    BusinessSettingsChanges,
    BusinessView,
    CreateBusinessCommand,
    CreateBusinessRequest,
    InviteStaffCommand,
    InviteStaffRequest,
    RemoveMemberCommand,
    UpdateBusinessSettingsCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_create_business_body = build_json_body_dependency(CreateBusinessRequest)
read_business_settings_body = build_json_body_dependency(BusinessSettingsChanges)
read_invite_staff_body = build_json_body_dependency(InviteStaffRequest)


def build_business_router(
    create_business_operator: OperatorContract[CreateBusinessCommand, BusinessView],
    list_my_businesses_operator: OperatorContract[UserId, list[BusinessView]],
    get_business_operator: OperatorContract[BusinessQuery, BusinessView],
    update_business_settings_operator: OperatorContract[
        UpdateBusinessSettingsCommand,
        BusinessView,
    ],
    invite_staff_operator: OperatorContract[InviteStaffCommand, BusinessView],
    remove_member_operator: OperatorContract[RemoveMemberCommand, BusinessView],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (all require a bearer token):
        POST   /v1/businesses                                  create (201)
        GET    /v1/businesses                                  my businesses
        GET    /v1/businesses/{business_id}                    one business
        PATCH  /v1/businesses/{business_id}                    owner: settings
        POST   /v1/businesses/{business_id}/members            owner: invite staff
        DELETE /v1/businesses/{business_id}/members/{user_id}  owner: remove member
    """

    router = APIRouter(tags=["businesses"])

    @router.post(
        "/v1/businesses",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(CreateBusinessRequest),
    )
    def create_business(
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CreateBusinessRequest, Depends(read_create_business_body)],
    ) -> BusinessView:
        return create_business_operator.operate(
            CreateBusinessCommand(user_id=user_id, details=body)
        )

    @router.get("/v1/businesses")
    def list_my_businesses(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> list[BusinessView]:
        return list_my_businesses_operator.operate(user_id)

    @router.get("/v1/businesses/{business_id}")
    def get_business(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> BusinessView:
        return get_business_operator.operate(
            BusinessQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.patch(
        "/v1/businesses/{business_id}",
        openapi_extra=describe_json_body(BusinessSettingsChanges),
    )
    def update_business_settings(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[BusinessSettingsChanges, Depends(read_business_settings_body)],
    ) -> BusinessView:
        return update_business_settings_operator.operate(
            UpdateBusinessSettingsCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                changes=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/members",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(InviteStaffRequest),
    )
    def invite_staff(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[InviteStaffRequest, Depends(read_invite_staff_body)],
    ) -> BusinessView:
        return invite_staff_operator.operate(
            InviteStaffCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                invitation=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete("/v1/businesses/{business_id}/members/{user_id}")
    def remove_member(
        request: Request,
        business_id: str,
        user_id: str,
        current_user_id: Annotated[UserId, Depends(current_user)],
    ) -> BusinessView:
        return remove_member_operator.operate(
            RemoveMemberCommand(
                user_id=current_user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                member_user_id=parse_path_identifier(user_id, UserId, "Member"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
