"""Settings → Integrations → API keys: the keys of a business (owners)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.integrations import ApiKeyScope, ApiKeyStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.integrations.constrained_integers import (
    ApiKeyCount,
    PublicApiRequestsPerMinute,
)
from app.schemas.typings.integrations.constrained_strings import (
    ApiKeyName,
    ApiKeyPrefix,
    ApiKeyToken,
)
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.users.prefixed_id import UserId


class ApiKeyView(ImmutableDTO):
    """A key as the cabinet lists it: never its secret, only its prefix."""

    id: ApiKeyId
    name: ApiKeyName
    prefix: ApiKeyPrefix
    scopes: list[ApiKeyScope]
    status: ApiKeyStatus
    created_at: Microseconds
    last_used_at: Microseconds | None = None
    revoked_at: Microseconds | None = None


class ApiKeyList(ImmutableDTO):
    """The business's keys, newest first, with the scopes a key may get."""

    items: list[ApiKeyView] = Field(default_factory=list[ApiKeyView])
    scopes: list[ApiKeyScope]
    max_keys: ApiKeyCount
    requests_per_minute: PublicApiRequestsPerMinute


class ApiKeyRequest(ImmutableDTO):
    """Body of a new key: what it is for and what it may do."""

    name: ApiKeyName
    scopes: list[ApiKeyScope] = Field(min_length=1)


class ApiKeysQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class CreateApiKeyCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: ApiKeyRequest
    client_ip_address: ClientIpAddress | None = None


class ApiKeyCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    api_key_id: ApiKeyId
    client_ip_address: ClientIpAddress | None = None


class CreatedApiKey(ImmutableDTO):
    """A new key with its secret token: shown this once, stored only hashed."""

    api_key: ApiKeyView
    token: ApiKeyToken
