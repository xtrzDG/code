"""Settings → Integrations → API keys (cabinet, bearer token, owners only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.integrations.api_key_views import (
    ApiKeyCommand,
    ApiKeyList,
    ApiKeyRequest,
    ApiKeysQuery,
    CreateApiKeyCommand,
    CreatedApiKey,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.users.prefixed_id import UserId

API_KEYS_PATH: str = "/v1/businesses/{business_id}/api-keys"

read_api_key_body = build_json_body_dependency(ApiKeyRequest)


def build_api_key_router(
    *,
    current_user: CurrentUserDependency,
    list_api_keys: OperatorContract[ApiKeysQuery, ApiKeyList],
    create_api_key: OperatorContract[CreateApiKeyCommand, CreatedApiKey],
    revoke_api_key: OperatorContract[ApiKeyCommand, None],
) -> APIRouter:
    """
    Routes of the business's API keys (owners; staff get 403):
        GET    .../api-keys          the keys (never their secrets) and scopes
        POST   .../api-keys          {name, scopes}: the key, its token shown
                                     once (201)
        DELETE .../api-keys/{id}     revoke at once (204)
    """

    router = APIRouter(tags=["api-keys"], responses=standard_error_responses())

    @router.get(API_KEYS_PATH)
    def list_business_api_keys(
        business_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> ApiKeyList:
        return list_api_keys.operate(
            ApiKeysQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.post(
        API_KEYS_PATH,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(ApiKeyRequest),
    )
    def create_business_api_key(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ApiKeyRequest, Depends(read_api_key_body)],
    ) -> CreatedApiKey:
        return create_api_key.operate(
            CreateApiKeyCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(
        f"{API_KEYS_PATH}/{{api_key_id}}", status_code=status.HTTP_204_NO_CONTENT
    )
    def revoke_business_api_key(
        business_id: str,
        api_key_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        revoke_api_key.operate(
            ApiKeyCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                api_key_id=parse_path_identifier(api_key_id, ApiKeyId, "API key"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
