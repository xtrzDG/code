"""A fresh token for the signed-in session right after it proved itself."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.sessions import RotateSessionCommand
from app.schemas.dto.users import LoginSessionView
from app.schemas.typings.users.prefixed_id import UserId


def build_session_rotation_router(
    rotate_session_operator: OperatorContract[RotateSessionCommand, LoginSessionView],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        POST /v1/auth/session/rotate  swap the request's session token for
                                      a new one (same level, device and
                                      expiries; the old token ends after
                                      30 s as one factor) once the person
                                      confirmed it is them (step-up)
                                      within the last minutes; the
                                      cabinet's server puts the new token
                                      into its cookie (409 for a session
                                      without a recent proof)
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.post("/v1/auth/session/rotate")
    def rotate_session(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> LoginSessionView:
        return rotate_session_operator.operate(RotateSessionCommand(user_id=user_id))

    return router
