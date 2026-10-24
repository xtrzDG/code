"""A brand's team: owners and regional managers (cabinet, bearer token)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.brand_routes import BRAND_OWNER_ACTION, BRAND_PATH, brand_of
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.brands.brand_commands import (
    ChangeBrandMemberCommand,
    InviteBrandMemberCommand,
    RemoveBrandMemberCommand,
)
from app.schemas.dto.brands.brand_requests import (
    ChangeBrandMemberRequest,
    InviteBrandMemberRequest,
)
from app.schemas.dto.brands.brand_views import BrandView
from app.schemas.typings.users.prefixed_id import UserId

MEMBER_PATH: str = f"{BRAND_PATH}/members/{{user_id}}"
read_invite_body = build_json_body_dependency(InviteBrandMemberRequest)
read_change_body = build_json_body_dependency(ChangeBrandMemberRequest)


def build_brand_team_router(
    *,
    current_user: CurrentUserDependency,
    invite_member: OperatorContract[InviteBrandMemberCommand, BrandView],
    change_member: OperatorContract[ChangeBrandMemberCommand, BrandView],
    remove_member: OperatorContract[RemoveBrandMemberCommand, None],
) -> APIRouter:
    """
    Routes (brand owners, after a fresh sign-in; a member may leave):
        POST   {B}/members              add an owner or a regional manager
        PATCH  {B}/members/{user_id}    change a role or a manager's locations
        DELETE {B}/members/{user_id}    take someone off the team (or leave)

    The brand keeps at least one owner (409). A manager reaches only the
    locations assigned to them; every change shows in the audit log of
    each location it opens or closes.
    """

    router = APIRouter(tags=["brands"], responses=standard_error_responses())

    @router.post(
        f"{BRAND_PATH}/members",
        description=BRAND_OWNER_ACTION,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(InviteBrandMemberRequest),
    )
    def invite_brand_member(
        request: Request,
        brand_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[InviteBrandMemberRequest, Depends(read_invite_body)],
    ) -> BrandView:
        return invite_member.operate(
            InviteBrandMemberCommand(
                user_id=user_id,
                brand_id=brand_of(brand_id),
                invitation=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.patch(
        MEMBER_PATH,
        description=BRAND_OWNER_ACTION,
        openapi_extra=describe_json_body(ChangeBrandMemberRequest),
    )
    def change_brand_member(
        request: Request,
        brand_id: str,
        user_id: str,
        current_user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ChangeBrandMemberRequest, Depends(read_change_body)],
    ) -> BrandView:
        return change_member.operate(
            ChangeBrandMemberCommand(
                user_id=current_user_id,
                brand_id=brand_of(brand_id),
                member_user_id=parse_path_identifier(user_id, UserId, "Member"),
                change=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(
        MEMBER_PATH,
        description=f"{BRAND_OWNER_ACTION} A member who leaves (removes themself) "
        "needs neither.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def remove_brand_member(
        request: Request,
        brand_id: str,
        user_id: str,
        current_user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        remove_member.operate(
            RemoveBrandMemberCommand(
                user_id=current_user_id,
                brand_id=brand_of(brand_id),
                member_user_id=parse_path_identifier(user_id, UserId, "Member"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
