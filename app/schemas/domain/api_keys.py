"""API keys of the public API (migration 1181)."""

from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.integrations import ApiKeyScope, ApiKeyStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.constrained_strings import (
    ApiKeyName,
    ApiKeyPrefix,
    ApiKeySecretHash,
)
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.users.prefixed_id import UserId


class ApiKeyDocument(BaseDocument):
    """
    One API key of a business (a business collection). The key itself is
    shown once, when it is made; only its scrypt digest (`secret_hash`, looked up
    across businesses when a request comes) and its public `prefix` are
    stored. `scopes` say what it may read or create. A REVOKED key is
    refused. `last_used_at` is written at most once a minute.
    """

    id: ApiKeyId = Field(default_factory=ApiKeyId)
    business_id: BusinessId
    name: ApiKeyName
    prefix: ApiKeyPrefix
    secret_hash: ApiKeySecretHash
    scopes: list[ApiKeyScope] = Field(min_length=1)
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    created_by: UserId
    last_used_at: Microseconds | None = None
    revoked_at: Microseconds | None = None
    revoked_by: UserId | None = None
