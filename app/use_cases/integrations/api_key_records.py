"""
The API keys' shared steps: their cabinet view, the cap, and what a key
may do (its scopes, refused with 403 `missing_scope`).
"""

from app.contracts.repositories.integration_repositories import ApiKeyRepoContract
from app.schemas.constants.integrations import ApiKeyScope, ApiKeyStatus
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.integrations.api_key_views import ApiKeyView
from app.schemas.dto.public_api.access import ApiKeyPrincipal
from app.schemas.exceptions.application_errors import AccessDeniedError, ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.integrations.constrained_integers import ApiKeyCount
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage

MAX_API_KEYS: ApiKeyCount = ApiKeyCount(10)
API_KEY_ENTITY: AuditEntityName = AuditEntityName("api_key")
TOO_MANY_MESSAGE: str = "A business has at most 10 active API keys; revoke one first."
MISSING_SCOPE_MESSAGE: str = "This API key may not do that; give it the scope."


def api_key_view(api_key: ApiKeyDocument) -> ApiKeyView:
    return ApiKeyView(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        scopes=api_key.scopes,
        status=api_key.status,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
    )


def granted_scopes(scopes: list[ApiKeyScope]) -> list[ApiKeyScope]:
    """The scopes once each, in the catalog's order."""

    return [scope for scope in ApiKeyScope if scope in scopes]


def refuse_when_full(api_key_repo: ApiKeyRepoContract, business_id: BusinessId) -> None:
    active = [
        api_key
        for api_key in api_key_repo.list_by_business(business_id)
        if api_key.status is ApiKeyStatus.ACTIVE
    ]
    if len(active) >= int(MAX_API_KEYS):
        raise ConflictError(
            TOO_MANY_MESSAGE,
            reasons=[
                ErrorReason(
                    code=ErrorReasonCode("api_key_limit_reached"),
                    message=ErrorReasonMessage(TOO_MANY_MESSAGE),
                    details=[ErrorReasonDetail(str(int(MAX_API_KEYS)))],
                )
            ],
        )


def require_scope(principal: ApiKeyPrincipal, scope: ApiKeyScope) -> None:
    """
    Raises:
        AccessDeniedError: the key was not given `scope` (403 missing_scope,
            the scope in its details).
    """

    if scope in principal.scopes:
        return

    raise AccessDeniedError(
        MISSING_SCOPE_MESSAGE,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode("missing_scope"),
                message=ErrorReasonMessage(MISSING_SCOPE_MESSAGE),
                details=[ErrorReasonDetail(scope.value)],
            )
        ],
    )
