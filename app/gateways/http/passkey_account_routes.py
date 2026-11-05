"""The signed-in person's passkeys (Account → Security)."""

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
from app.schemas.dto.passkeys import (
    FinishPasskeyRegistrationCommand,
    FinishPasskeyRegistrationRequest,
    PasskeyAddedView,
    PasskeyCommand,
    PasskeyListView,
    PasskeyRegistrationView,
    PasskeyView,
    RemovePasskeyCommand,
    RenamePasskeyCommand,
    RenamePasskeyRequest,
)
from app.schemas.typings.passkeys.prefixed_id import PasskeyId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.user_agents import read_user_agent

read_registration_body = build_json_body_dependency(FinishPasskeyRegistrationRequest)
read_rename_body = build_json_body_dependency(RenamePasskeyRequest)
PASSKEY_LABEL: str = "Passkey"


def build_passkey_account_router(
    list_passkeys_operator: OperatorContract[UserId, PasskeyListView],
    start_passkey_registration_operator: OperatorContract[
        PasskeyCommand, PasskeyRegistrationView
    ],
    finish_passkey_registration_operator: OperatorContract[
        FinishPasskeyRegistrationCommand, PasskeyAddedView
    ],
    rename_passkey_operator: OperatorContract[RenamePasskeyCommand, PasskeyView],
    remove_passkey_operator: OperatorContract[RemovePasskeyCommand, None],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        GET    /v1/me/passkeys                the person's passkeys
        POST   /v1/me/passkeys/registration   options of a new passkey (step-up)
        POST   /v1/me/passkeys                the new passkey (201; recovery
               codes once with the first second factor)
        PATCH  /v1/me/passkeys/{passkey_id}   rename one
        DELETE /v1/me/passkeys/{passkey_id}   remove one (step-up; 204)
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.get("/v1/me/passkeys")
    def list_passkeys(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PasskeyListView:
        return list_passkeys_operator.operate(user_id)

    @router.post("/v1/me/passkeys/registration")
    def start_passkey_registration(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PasskeyRegistrationView:
        return start_passkey_registration_operator.operate(
            PasskeyCommand(
                user_id=user_id, client_ip_address=read_client_ip_address(request)
            )
        )

    @router.post(
        "/v1/me/passkeys",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(FinishPasskeyRegistrationRequest),
    )
    def finish_passkey_registration(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            FinishPasskeyRegistrationRequest, Depends(read_registration_body)
        ],
    ) -> PasskeyAddedView:
        return finish_passkey_registration_operator.operate(
            FinishPasskeyRegistrationCommand(
                user_id=user_id,
                passkey_challenge_id=body.passkey_challenge_id,
                credential=body.credential,
                name=body.name,
                client_ip_address=read_client_ip_address(request),
                user_agent=read_user_agent(request.headers.get("user-agent")),
            )
        )

    @router.patch(
        "/v1/me/passkeys/{passkey_id}",
        openapi_extra=describe_json_body(RenamePasskeyRequest),
    )
    def rename_passkey(
        passkey_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[RenamePasskeyRequest, Depends(read_rename_body)],
    ) -> PasskeyView:
        return rename_passkey_operator.operate(
            RenamePasskeyCommand(
                user_id=user_id,
                passkey_id=parse_path_identifier(passkey_id, PasskeyId, PASSKEY_LABEL),
                name=body.name,
            )
        )

    @router.delete(
        "/v1/me/passkeys/{passkey_id}", status_code=status.HTTP_204_NO_CONTENT
    )
    def remove_passkey(
        passkey_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        remove_passkey_operator.operate(
            RemovePasskeyCommand(
                user_id=user_id,
                passkey_id=parse_path_identifier(passkey_id, PasskeyId, PASSKEY_LABEL),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
