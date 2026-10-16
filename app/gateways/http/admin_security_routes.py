"""Platform admin: the key ring and re-encrypting the stored secrets."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import read_client_ip_address
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.key_rotation import (
    EncryptionKeysQuery,
    EncryptionKeysView,
    KeyRotationStarted,
    StartKeyRotationCommand,
)
from app.schemas.typings.users.prefixed_id import UserId

type GetEncryptionKeysOperator = OperatorContract[
    EncryptionKeysQuery, EncryptionKeysView
]
type StartKeyRotationOperator = OperatorContract[
    StartKeyRotationCommand, KeyRotationStarted
]


def build_admin_security_router(
    get_encryption_keys_operator: GetEncryptionKeysOperator,
    start_key_rotation_operator: StartKeyRotationOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a platform admin; others get 403):
        GET  /v1/admin/security/encryption-keys         how many keys the
             ring holds (never the keys) and the latest re-encryption run
        POST /v1/admin/security/encryption-keys/rotate  seal every stored
             secret again with the current key (a queued job, 202; audited;
             409 while a run is in progress)
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get("/v1/admin/security/encryption-keys")
    def get_encryption_keys(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> EncryptionKeysView:
        return get_encryption_keys_operator.operate(
            EncryptionKeysQuery(user_id=user_id)
        )

    @router.post(
        "/v1/admin/security/encryption-keys/rotate",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def start_key_rotation(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> KeyRotationStarted:
        return start_key_rotation_operator.operate(
            StartKeyRotationCommand(
                user_id=user_id,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
