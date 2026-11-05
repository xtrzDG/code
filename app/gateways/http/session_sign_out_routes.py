"""The signed-in person signs out everywhere, this device too."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import read_client_ip_address
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.sessions import RevokeAllSessionsCommand, RevokedSessionsView
from app.schemas.typings.users.prefixed_id import UserId


def build_session_sign_out_router(
    revoke_all_sessions_operator: OperatorContract[
        RevokeAllSessionsCommand, RevokedSessionsView
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        POST /v1/me/sessions/revoke-all  end every session of the person,
                                         the request's own too (audited);
                                         the cabinet then drops its cookie
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.post("/v1/me/sessions/revoke-all")
    def revoke_all_sessions(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> RevokedSessionsView:
        return revoke_all_sessions_operator.operate(
            RevokeAllSessionsCommand(
                user_id=user_id,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
