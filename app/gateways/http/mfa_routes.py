"""Two-factor sign-in, a person's authenticator and confirming sensitive actions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.mfa import (
    AccountSecurityView,
    ConfirmTotpCommand,
    ConfirmTotpRequest,
    MfaChangeCommand,
    RecoveryCodesView,
    SessionAssuranceView,
    StartMfaEnrollmentCommand,
    StartMfaEnrollmentRequest,
    StartStepUpCommand,
    StepUpChallengeView,
    TotpEnrollmentView,
    VerifyMfaLoginCommand,
    VerifyMfaLoginRequest,
    VerifyStepUpCommand,
    VerifyStepUpRequest,
)
from app.schemas.dto.users import LoginSessionView
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.user_agents import read_user_agent

read_verify_mfa_body = build_json_body_dependency(VerifyMfaLoginRequest)
read_enroll_body = build_json_body_dependency(StartMfaEnrollmentRequest)
read_confirm_body = build_json_body_dependency(ConfirmTotpRequest)
read_step_up_body = build_json_body_dependency(VerifyStepUpRequest)


def build_mfa_router(
    verify_mfa_login_operator: OperatorContract[
        VerifyMfaLoginCommand, LoginSessionView
    ],
    start_mfa_login_enrollment_operator: OperatorContract[
        StartMfaEnrollmentCommand, TotpEnrollmentView
    ],
    get_account_security_operator: OperatorContract[UserId, AccountSecurityView],
    start_totp_enrollment_operator: OperatorContract[UserId, TotpEnrollmentView],
    confirm_totp_enrollment_operator: OperatorContract[
        ConfirmTotpCommand, RecoveryCodesView
    ],
    remove_totp_factor_operator: OperatorContract[MfaChangeCommand, None],
    regenerate_recovery_codes_operator: OperatorContract[
        MfaChangeCommand, RecoveryCodesView
    ],
    start_step_up_operator: OperatorContract[StartStepUpCommand, StepUpChallengeView],
    verify_step_up_operator: OperatorContract[
        VerifyStepUpCommand, SessionAssuranceView
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        POST   /v1/auth/mfa/verify           second sign-in step: authenticator
               or recovery code -> the session (token once)
        POST   /v1/auth/mfa/enroll           a platform admin without an
               authenticator sets one up while signing in
        POST   /v1/auth/step-up              how to confirm it is you (sends a
               login code when there is no authenticator)
        POST   /v1/auth/step-up/verify       confirm: sensitive actions work again
        GET    /v1/me/security               the person's two-factor sign-in
        POST   /v1/me/mfa/totp               start setting up an authenticator
        POST   /v1/me/mfa/totp/confirm       its first code turns it on (recovery
               codes once)
        DELETE /v1/me/mfa/totp               remove it (step-up; 204)
        POST   /v1/me/mfa/recovery-codes     a new set of recovery codes (step-up)
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.post(
        "/v1/auth/mfa/verify", openapi_extra=describe_json_body(VerifyMfaLoginRequest)
    )
    def verify_mfa_login(
        request: Request,
        body: Annotated[VerifyMfaLoginRequest, Depends(read_verify_mfa_body)],
    ) -> LoginSessionView:
        return verify_mfa_login_operator.operate(
            VerifyMfaLoginCommand(
                mfa_challenge_id=body.mfa_challenge_id,
                code=body.code,
                recovery_code=body.recovery_code,
                client_ip_address=read_client_ip_address(request),
                user_agent=read_user_agent(request.headers.get("user-agent")),
            )
        )

    @router.post(
        "/v1/auth/mfa/enroll",
        openapi_extra=describe_json_body(StartMfaEnrollmentRequest),
    )
    def start_mfa_login_enrollment(
        request: Request,
        body: Annotated[StartMfaEnrollmentRequest, Depends(read_enroll_body)],
    ) -> TotpEnrollmentView:
        return start_mfa_login_enrollment_operator.operate(
            StartMfaEnrollmentCommand(
                mfa_challenge_id=body.mfa_challenge_id,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post("/v1/auth/step-up")
    def start_step_up(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> StepUpChallengeView:
        return start_step_up_operator.operate(
            StartStepUpCommand(
                user_id=user_id, client_ip_address=read_client_ip_address(request)
            )
        )

    @router.post(
        "/v1/auth/step-up/verify",
        openapi_extra=describe_json_body(VerifyStepUpRequest),
    )
    def verify_step_up(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[VerifyStepUpRequest, Depends(read_step_up_body)],
    ) -> SessionAssuranceView:
        return verify_step_up_operator.operate(
            VerifyStepUpCommand(
                user_id=user_id,
                code=body.code,
                recovery_code=body.recovery_code,
                challenge_id=body.challenge_id,
                login_code=body.login_code,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/me/security")
    def get_account_security(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AccountSecurityView:
        return get_account_security_operator.operate(user_id)

    @router.post("/v1/me/mfa/totp")
    def start_totp_enrollment(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> TotpEnrollmentView:
        return start_totp_enrollment_operator.operate(user_id)

    @router.post(
        "/v1/me/mfa/totp/confirm", openapi_extra=describe_json_body(ConfirmTotpRequest)
    )
    def confirm_totp_enrollment(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ConfirmTotpRequest, Depends(read_confirm_body)],
    ) -> RecoveryCodesView:
        return confirm_totp_enrollment_operator.operate(
            ConfirmTotpCommand(
                user_id=user_id,
                code=body.code,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete("/v1/me/mfa/totp", status_code=status.HTTP_204_NO_CONTENT)
    def remove_totp_factor(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        remove_totp_factor_operator.operate(
            MfaChangeCommand(
                user_id=user_id, client_ip_address=read_client_ip_address(request)
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post("/v1/me/mfa/recovery-codes")
    def regenerate_recovery_codes(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> RecoveryCodesView:
        return regenerate_recovery_codes_operator.operate(
            MfaChangeCommand(
                user_id=user_id, client_ip_address=read_client_ip_address(request)
            )
        )

    return router
