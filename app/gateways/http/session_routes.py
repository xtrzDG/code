"""The signed-in person's devices: list them, end one, end all the others."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.sessions import (
    RevokedSessionsView,
    RevokeOtherSessionsCommand,
    RevokeSessionCommand,
    SessionsQuery,
    UserSessionList,
)
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId


def build_sessions_router(
    list_my_sessions_operator: OperatorContract[SessionsQuery, UserSessionList],
    revoke_session_operator: OperatorContract[RevokeSessionCommand, None],
    revoke_other_sessions_operator: OperatorContract[
        RevokeOtherSessionsCommand, RevokedSessionsView
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        GET    /v1/me/sessions                the person's signed-in devices
                                              (this one first)
        DELETE /v1/me/sessions/{session_id}   end one of them (204; audited)
        POST   /v1/me/sessions/revoke-others  end every one but this (audited)
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.get("/v1/me/sessions")
    def list_my_sessions(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> UserSessionList:
        return list_my_sessions_operator.operate(SessionsQuery(user_id=user_id))

    @router.delete(
        "/v1/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT
    )
    def revoke_session(
        session_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        revoke_session_operator.operate(
            RevokeSessionCommand(
                user_id=user_id,
                session_id=parse_path_identifier(session_id, UserSessionId, "Session"),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post("/v1/me/sessions/revoke-others")
    def revoke_other_sessions(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> RevokedSessionsView:
        return revoke_other_sessions_operator.operate(
            RevokeOtherSessionsCommand(
                user_id=user_id,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
