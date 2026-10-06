"""Businesses (tenants), their settings and team."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.entity_tags import (
    ETAG_RESPONSE_HEADER,
    IfMatchHeader,
    read_if_match_revisions,
    tag_response_with_revision,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
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
    ChangeMemberRoleCommand,
    CreateBusinessCommand,
    CreateBusinessRequest,
    InviteStaffCommand,
    InviteStaffRequest,
    MemberRoleChange,
    RemoveMemberCommand,
    UpdateBusinessSettingsCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_create_business_body = build_json_body_dependency(CreateBusinessRequest)
read_business_settings_body = build_json_body_dependency(BusinessSettingsChanges)
read_invite_staff_body = build_json_body_dependency(InviteStaffRequest)
read_member_role_body = build_json_body_dependency(MemberRoleChange)


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
    change_member_role_operator: OperatorContract[
        ChangeMemberRoleCommand,
        BusinessView,
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (all require a bearer token):
        POST   /v1/businesses                                  create (201)
        GET    /v1/businesses                                  my businesses
        GET    /v1/businesses/{business_id}                    one business
        PATCH  /v1/businesses/{business_id}                    owner: settings
        POST   /v1/businesses/{business_id}/members            owner: invite a
                                                               member (staff or
                                                               owner)
        PATCH  /v1/businesses/{business_id}/members/{user_id}  owner: change role
        DELETE /v1/businesses/{business_id}/members/{user_id}  owner: remove member

    The last owner of a business can be neither removed nor made staff (409).
    A settings change carries the `revision` it was made from as
    `expected_revision`; when someone saved the business since, nothing
    changes and the answer is 409 with the reason `stale_revision`. GET and
    PATCH of one business answer its revision as ETag too, and a PATCH
    with If-Match naming another revision is refused with 412
    (app/gateways/http/entity_tags.py).
    """

    router = APIRouter(tags=["businesses"], responses=standard_error_responses())

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

    @router.get(
        "/v1/businesses/{business_id}",
        responses={200: {"headers": ETAG_RESPONSE_HEADER}},
    )
    def get_business(
        business_id: str,
        response: Response,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> BusinessView:
        business: BusinessView = get_business_operator.operate(
            BusinessQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )
        tag_response_with_revision(response, business.revision)
        return business

    @router.patch(
        "/v1/businesses/{business_id}",
        openapi_extra=describe_json_body(BusinessSettingsChanges),
        responses={
            200: {"headers": ETAG_RESPONSE_HEADER},
            **standard_error_responses(412),
        },
    )
    def update_business_settings(
        request: Request,
        response: Response,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[BusinessSettingsChanges, Depends(read_business_settings_body)],
        if_match: IfMatchHeader = None,
    ) -> BusinessView:
        business: BusinessView = update_business_settings_operator.operate(
            UpdateBusinessSettingsCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                changes=body,
                client_ip_address=read_client_ip_address(request),
                if_match_revisions=read_if_match_revisions(if_match),
            )
        )
        tag_response_with_revision(response, business.revision)
        return business

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

    @router.patch(
        "/v1/businesses/{business_id}/members/{user_id}",
        openapi_extra=describe_json_body(MemberRoleChange),
    )
    def change_member_role(
        request: Request,
        business_id: str,
        user_id: str,
        current_user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[MemberRoleChange, Depends(read_member_role_body)],
    ) -> BusinessView:
        return change_member_role_operator.operate(
            ChangeMemberRoleCommand(
                user_id=current_user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                member_user_id=parse_path_identifier(user_id, UserId, "Member"),
                change=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(
        "/v1/businesses/{business_id}/members/{user_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def remove_member(
        request: Request,
        business_id: str,
        user_id: str,
        current_user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        remove_member_operator.operate(
            RemoveMemberCommand(
                user_id=current_user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                member_user_id=parse_path_identifier(user_id, UserId, "Member"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
