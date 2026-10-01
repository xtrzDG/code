"""Sign-in with a one-time code, sessions and the signed-in user's profile."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import (
    CurrentUserDependency,
    parse_bearer_token,
)
from app.schemas.dto.users import (
    CurrentUserView,
    LoginSessionView,
    LogoutCommand,
    OtpChallengeView,
    StartOtpLoginCommand,
    UpdateCurrentUserCommand,
    UpdateCurrentUserRequest,
    UserView,
    VerifyOtpLoginCommand,
    VerifyOtpLoginRequest,
)
from app.schemas.typings.users.prefixed_id import UserId

read_start_otp_login_body = build_json_body_dependency(StartOtpLoginCommand)
read_verify_otp_login_body = build_json_body_dependency(VerifyOtpLoginRequest)
read_update_current_user_body = build_json_body_dependency(UpdateCurrentUserRequest)


def build_users_router(
    start_otp_login_operator: OperatorContract[StartOtpLoginCommand, OtpChallengeView],
    verify_otp_login_operator: OperatorContract[
        VerifyOtpLoginCommand,
        LoginSessionView,
    ],
    logout_operator: OperatorContract[LogoutCommand, None],
    get_current_user_operator: OperatorContract[UserId, CurrentUserView],
    update_current_user_operator: OperatorContract[
        UpdateCurrentUserCommand,
        UserView,
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        POST  /v1/auth/otp/start   send a login code (phone of any country or e-mail)
        POST  /v1/auth/otp/verify  check the code, return a bearer token once
        POST  /v1/auth/logout      end the current session (204)
        GET   /v1/me               the user and their businesses
        PATCH /v1/me               change display name or interface language
    """

    router = APIRouter(tags=["auth"])

    @router.post(
        "/v1/auth/otp/start",
        status_code=status.HTTP_200_OK,
        openapi_extra=describe_json_body(StartOtpLoginCommand),
    )
    def start_otp_login(
        body: Annotated[StartOtpLoginCommand, Depends(read_start_otp_login_body)],
    ) -> OtpChallengeView:
        return start_otp_login_operator.operate(body)

    @router.post(
        "/v1/auth/otp/verify",
        status_code=status.HTTP_200_OK,
        openapi_extra=describe_json_body(VerifyOtpLoginRequest),
    )
    def verify_otp_login(
        request: Request,
        body: Annotated[VerifyOtpLoginRequest, Depends(read_verify_otp_login_body)],
    ) -> LoginSessionView:
        return verify_otp_login_operator.operate(
            VerifyOtpLoginCommand(
                challenge_id=body.challenge_id,
                code=body.code,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post("/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(
        authorization: Annotated[str | None, Header()] = None,
    ) -> Response:
        logout_operator.operate(
            LogoutCommand(access_token=parse_bearer_token(authorization))
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/v1/me")
    def get_current_user(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CurrentUserView:
        return get_current_user_operator.operate(user_id)

    @router.patch(
        "/v1/me",
        openapi_extra=describe_json_body(UpdateCurrentUserRequest),
    )
    def update_current_user(
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            UpdateCurrentUserRequest,
            Depends(read_update_current_user_body),
        ],
    ) -> UserView:
        return update_current_user_operator.operate(
            UpdateCurrentUserCommand(
                user_id=user_id,
                display_name=body.display_name,
                locale=body.locale,
            )
        )

    return router
