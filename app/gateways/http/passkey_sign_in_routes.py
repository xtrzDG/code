"""Passkeys at the second step of a sign-in and at step-up confirmations."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.mfa import SessionAssuranceView
from app.schemas.dto.passkeys import (
    FinishPasskeyEnrollmentCommand,
    FinishPasskeyEnrollmentRequest,
    PasskeyAssertionOptionsView,
    PasskeyCommand,
    PasskeyRegistrationView,
    PasskeySignInStepCommand,
    PasskeySignInStepRequest,
    VerifyPasskeySignInCommand,
    VerifyPasskeySignInRequest,
    VerifyPasskeyStepUpCommand,
    VerifyPasskeyStepUpRequest,
)
from app.schemas.dto.users import LoginSessionView
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.user_agents import read_user_agent

read_step_body = build_json_body_dependency(PasskeySignInStepRequest)
read_verify_body = build_json_body_dependency(VerifyPasskeySignInRequest)
read_enrollment_body = build_json_body_dependency(FinishPasskeyEnrollmentRequest)
read_step_up_body = build_json_body_dependency(VerifyPasskeyStepUpRequest)


def build_passkey_sign_in_router(
    start_passkey_sign_in_operator: OperatorContract[
        PasskeySignInStepCommand, PasskeyAssertionOptionsView
    ],
    verify_passkey_sign_in_operator: OperatorContract[
        VerifyPasskeySignInCommand, LoginSessionView
    ],
    start_passkey_enrollment_operator: OperatorContract[
        PasskeySignInStepCommand, PasskeyRegistrationView
    ],
    finish_passkey_enrollment_operator: OperatorContract[
        FinishPasskeyEnrollmentCommand, LoginSessionView
    ],
    start_passkey_step_up_operator: OperatorContract[
        PasskeyCommand, PasskeyAssertionOptionsView
    ],
    verify_passkey_step_up_operator: OperatorContract[
        VerifyPasskeyStepUpCommand, SessionAssuranceView
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        POST /v1/auth/mfa/passkey/options        the second step of a
             sign-in asks for passkey options
        POST /v1/auth/mfa/passkey/verify         the passkey's answer -> the
             session (token once)
        POST /v1/auth/mfa/passkey/enroll         a platform admin without a
             second factor starts adding a passkey while signing in
        POST /v1/auth/mfa/passkey/enroll/finish  the new passkey -> the
             session (recovery codes once)
        POST /v1/auth/step-up/passkey            options to confirm it is you
        POST /v1/auth/step-up/passkey/verify     the passkey's answer:
             sensitive actions work again
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.post(
        "/v1/auth/mfa/passkey/options",
        openapi_extra=describe_json_body(PasskeySignInStepRequest),
    )
    def start_passkey_sign_in(
        request: Request,
        body: Annotated[PasskeySignInStepRequest, Depends(read_step_body)],
    ) -> PasskeyAssertionOptionsView:
        return start_passkey_sign_in_operator.operate(
            PasskeySignInStepCommand(
                mfa_challenge_id=body.mfa_challenge_id,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        "/v1/auth/mfa/passkey/verify",
        openapi_extra=describe_json_body(VerifyPasskeySignInRequest),
    )
    def verify_passkey_sign_in(
        request: Request,
        body: Annotated[VerifyPasskeySignInRequest, Depends(read_verify_body)],
    ) -> LoginSessionView:
        return verify_passkey_sign_in_operator.operate(
            VerifyPasskeySignInCommand(
                mfa_challenge_id=body.mfa_challenge_id,
                passkey_challenge_id=body.passkey_challenge_id,
                credential=body.credential,
                client_ip_address=read_client_ip_address(request),
                user_agent=read_user_agent(request.headers.get("user-agent")),
            )
        )

    @router.post(
        "/v1/auth/mfa/passkey/enroll",
        openapi_extra=describe_json_body(PasskeySignInStepRequest),
    )
    def start_passkey_enrollment(
        request: Request,
        body: Annotated[PasskeySignInStepRequest, Depends(read_step_body)],
    ) -> PasskeyRegistrationView:
        return start_passkey_enrollment_operator.operate(
            PasskeySignInStepCommand(
                mfa_challenge_id=body.mfa_challenge_id,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        "/v1/auth/mfa/passkey/enroll/finish",
        openapi_extra=describe_json_body(FinishPasskeyEnrollmentRequest),
    )
    def finish_passkey_enrollment(
        request: Request,
        body: Annotated[FinishPasskeyEnrollmentRequest, Depends(read_enrollment_body)],
    ) -> LoginSessionView:
        return finish_passkey_enrollment_operator.operate(
            FinishPasskeyEnrollmentCommand(
                mfa_challenge_id=body.mfa_challenge_id,
                passkey_challenge_id=body.passkey_challenge_id,
                credential=body.credential,
                name=body.name,
                client_ip_address=read_client_ip_address(request),
                user_agent=read_user_agent(request.headers.get("user-agent")),
            )
        )

    @router.post("/v1/auth/step-up/passkey")
    def start_passkey_step_up(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PasskeyAssertionOptionsView:
        return start_passkey_step_up_operator.operate(
            PasskeyCommand(
                user_id=user_id, client_ip_address=read_client_ip_address(request)
            )
        )

    @router.post(
        "/v1/auth/step-up/passkey/verify",
        openapi_extra=describe_json_body(VerifyPasskeyStepUpRequest),
    )
    def verify_passkey_step_up(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[VerifyPasskeyStepUpRequest, Depends(read_step_up_body)],
    ) -> SessionAssuranceView:
        return verify_passkey_step_up_operator.operate(
            VerifyPasskeyStepUpCommand(
                user_id=user_id,
                passkey_challenge_id=body.passkey_challenge_id,
                credential=body.credential,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
