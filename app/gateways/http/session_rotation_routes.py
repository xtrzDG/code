"""A fresh token for the signed-in session right after a proof raised it."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.sessions import RotateSessionCommand, RotateSessionRequest
from app.schemas.dto.users import LoginSessionView
from app.schemas.typings.users.prefixed_id import UserId


def build_session_rotation_router(
    rotate_session_operator: OperatorContract[RotateSessionCommand, LoginSessionView],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        POST /v1/auth/session/rotate  swap the request's session token for
                                      a new one with the one-time
                                      `rotation_ticket` the proof that
                                      raised the session to two factors
                                      answered (a step-up, a new
                                      authenticator or first passkey):
                                      the new token carries the two
                                      factors, device and expiries; the
                                      old one stays one factor without a
                                      proof and ends after 30 s; the
                                      cabinet's server puts the new token
                                      into its cookie (409 without a
                                      matching, unused, unexpired ticket
                                      of this session)
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.post("/v1/auth/session/rotate")
    def rotate_session(
        body: RotateSessionRequest,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> LoginSessionView:
        return rotate_session_operator.operate(
            RotateSessionCommand(user_id=user_id, rotation_ticket=body.rotation_ticket)
        )

    return router
