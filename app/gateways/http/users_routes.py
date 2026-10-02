"""Sign-in with a one-time code, sessions and the signed-in user's profile."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import (
    CurrentUserDependency,
    parse_bearer_token,
)
from app.schemas.dto.login_options import LoginOptionsQuery, LoginOptionsView
from app.schemas.dto.users import (
    CurrentUserView,
    LoginSessionView,
    LogoutCommand,
    OtpChallengeView,
    StartOtpLoginCommand,
    StartOtpLoginRequest,
    UpdateCurrentUserCommand,
    UpdateCurrentUserRequest,
    UserView,
    VerifyOtpLoginCommand,
    VerifyOtpLoginRequest,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.prefixed_id import UserId

read_start_otp_login_body = build_json_body_dependency(StartOtpLoginRequest)
read_verify_otp_login_body = build_json_body_dependency(VerifyOtpLoginRequest)
read_update_current_user_body = build_json_body_dependency(UpdateCurrentUserRequest)


def build_users_router(
    start_otp_login_operator: OperatorContract[StartOtpLoginCommand, OtpChallengeView],
    get_login_options_operator: OperatorContract[LoginOptionsQuery, LoginOptionsView],
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
        GET   /v1/auth/login-options  working login-code channels (?country_code=GE)
        POST  /v1/auth/otp/start   send a login code (phone of any country or e-mail)
        POST  /v1/auth/otp/verify  check the code, return a bearer token once
        POST  /v1/auth/logout      end the current session (204)
        GET   /v1/me               the user and their businesses
        PATCH /v1/me               change display name or interface language
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.get("/v1/auth/login-options")
    def get_login_options(
        country_code: Annotated[str | None, Query()] = None,
    ) -> LoginOptionsView:
        return get_login_options_operator.operate(
            LoginOptionsQuery(country_code=parse_country_code(country_code))
        )

    @router.post(
        "/v1/auth/otp/start",
        status_code=status.HTTP_200_OK,
        openapi_extra=describe_json_body(StartOtpLoginRequest),
    )
    def start_otp_login(
        request: Request,
        body: Annotated[StartOtpLoginRequest, Depends(read_start_otp_login_body)],
    ) -> OtpChallengeView:
        return start_otp_login_operator.operate(
            StartOtpLoginCommand(
                phone_number=body.phone_number,
                email=body.email,
                country_hint=body.country_hint,
                locale=body.locale,
                preferred_delivery_channel=body.preferred_delivery_channel,
                client_ip_address=read_client_ip_address(request),
            )
        )

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


def parse_country_code(raw_country_code: str | None) -> CountryCode | None:
    """`?country_code=ge` as an ISO code; blank means none; 422 when malformed."""

    if raw_country_code is None or raw_country_code.strip() == "":
        return None

    try:
        return CountryCode(raw_country_code.strip().upper())
    except ValueError as error:
        raise ValidationFailedError(
            "country_code must be a two-letter ISO 3166-1 code, like GE."
        ) from error
