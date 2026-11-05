"""The platform admin team (SUPER admins) and leaving a client's cabinet."""

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
from app.schemas.dto.platform_admins import (
    AddPlatformAdminCommand,
    AddPlatformAdminRequest,
    ChangePlatformAdminRoleCommand,
    ChangePlatformAdminRoleRequest,
    PlatformAdminTeamQuery,
    PlatformAdminTeamView,
    RemovePlatformAdminCommand,
)
from app.schemas.dto.support_access import CloseClientCabinetCommand
from app.schemas.typings.access.prefixed_id import PlatformAdminId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_add_body = build_json_body_dependency(AddPlatformAdminRequest)
read_role_body = build_json_body_dependency(ChangePlatformAdminRoleRequest)
type TeamOperator[Command] = OperatorContract[Command, PlatformAdminTeamView]


def build_admin_team_router(
    list_platform_admins_operator: TeamOperator[PlatformAdminTeamQuery],
    add_platform_admin_operator: TeamOperator[AddPlatformAdminCommand],
    change_platform_admin_role_operator: TeamOperator[ChangePlatformAdminRoleCommand],
    remove_platform_admin_operator: OperatorContract[RemovePlatformAdminCommand, None],
    close_client_cabinet_operator: OperatorContract[CloseClientCabinetCommand, None],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (platform admins; the team needs the SUPER role):
        GET    /v1/admin/team              the admin team
        POST   /v1/admin/team              add someone {phone_number | email,
                                           role} (step-up; audited)
        PATCH  /v1/admin/team/{admin_id}   another role {role} (step-up)
        DELETE /v1/admin/team/{admin_id}   take them off the team (204)
        DELETE /v1/admin/clients/{business_id}/access
                                           leave a client's cabinet (204)
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get("/v1/admin/team")
    def list_platform_admins(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PlatformAdminTeamView:
        return list_platform_admins_operator.operate(
            PlatformAdminTeamQuery(user_id=user_id)
        )

    @router.post(
        "/v1/admin/team", openapi_extra=describe_json_body(AddPlatformAdminRequest)
    )
    def add_platform_admin(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AddPlatformAdminRequest, Depends(read_add_body)],
    ) -> PlatformAdminTeamView:
        return add_platform_admin_operator.operate(
            AddPlatformAdminCommand(
                user_id=user_id,
                phone_number=body.phone_number,
                email=body.email,
                role=body.role,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.patch(
        "/v1/admin/team/{admin_id}",
        openapi_extra=describe_json_body(ChangePlatformAdminRoleRequest),
    )
    def change_platform_admin_role(
        admin_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ChangePlatformAdminRoleRequest, Depends(read_role_body)],
    ) -> PlatformAdminTeamView:
        return change_platform_admin_role_operator.operate(
            ChangePlatformAdminRoleCommand(
                user_id=user_id,
                admin_id=parse_path_identifier(admin_id, PlatformAdminId, "Admin"),
                role=body.role,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete("/v1/admin/team/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_platform_admin(
        admin_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        remove_platform_admin_operator.operate(
            RemovePlatformAdminCommand(
                user_id=user_id,
                admin_id=parse_path_identifier(admin_id, PlatformAdminId, "Admin"),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/v1/admin/clients/{business_id}/access",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def close_client_cabinet(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        close_client_cabinet_operator.operate(
            CloseClientCabinetCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
