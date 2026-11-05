"""Platform admin: a client team's sign-ins, and ending one member's sessions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.admin_sessions import (
    ClientMemberSessionList,
    ClientMembersQuery,
    EndMemberSessionsCommand,
)
from app.schemas.dto.sessions import RevokedSessionsView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

MEMBERS_PATH: str = "/v1/admin/clients/{business_id}/members"


def build_admin_member_session_router(
    list_client_member_sessions_operator: OperatorContract[
        ClientMembersQuery, ClientMemberSessionList
    ],
    end_member_sessions_operator: OperatorContract[
        EndMemberSessionsCommand, RevokedSessionsView
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a platform admin signed in with two factors):
        GET  …/members                          the team: role, name, masked
                                                login, live sessions, last use
                                                (admins who see clients)
        POST …/members/{member_user_id}/sessions/revoke
                                                end every session of that
                                                member (SUPER, step-up;
                                                audited in the platform's
                                                chain)
    (… is /v1/admin/clients/{business_id}).
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get(MEMBERS_PATH)
    def list_client_member_sessions(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ClientMemberSessionList:
        return list_client_member_sessions_operator.operate(
            ClientMembersQuery(
                user_id=user_id,
                client_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.post(f"{MEMBERS_PATH}/{{member_user_id}}/sessions/revoke")
    def end_member_sessions(
        request: Request,
        business_id: str,
        member_user_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> RevokedSessionsView:
        return end_member_sessions_operator.operate(
            EndMemberSessionsCommand(
                user_id=user_id,
                client_id=parse_path_identifier(business_id, BusinessId, "Business"),
                member_user_id=parse_path_identifier(member_user_id, UserId, "Member"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
