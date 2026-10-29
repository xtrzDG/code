from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import ApiKeyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.api_key_views import (
    CreateApiKeyCommand,
    CreatedApiKey,
)
from app.use_cases.integrations.api_key_records import (
    API_KEY_ENTITY,
    api_key_view,
    granted_scopes,
    refuse_when_full,
)
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.integrations.integration_secrets import hash_api_key, new_api_key


class CreateApiKeyUseCase(UseCaseContract[CreateApiKeyCommand, CreatedApiKey]):
    """
    A new API key of the business with the scopes the owner chose: a random
    token (`awk_<prefix>_<secret>`) shown this once; only its scrypt digest
    and its prefix are stored, so a leaked database holds no usable key. At
    most MAX_API_KEYS active keys (409 `api_key_limit_reached`). Owners
    only; audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        api_key_repo: ApiKeyRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._api_key_repo: ApiKeyRepoContract = api_key_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateApiKeyCommand) -> CreatedApiKey:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        refuse_when_full(self._api_key_repo, business.id)
        now: Microseconds = self._wall_clock.now_unix()
        token, prefix = new_api_key()
        api_key = ApiKeyDocument(
            business_id=business.id,
            name=input_data.request.name,
            prefix=prefix,
            secret_hash=hash_api_key(token),
            scopes=granted_scopes(input_data.request.scopes),
            created_by=input_data.user_id,
            created_at=now,
            updated_at=now,
        )
        self._api_key_repo.save(api_key)
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.CREATE,
                API_KEY_ENTITY,
                str(api_key.id),
                now,
                input_data.client_ip_address,
            )
        )
        return CreatedApiKey(api_key=api_key_view(api_key), token=token)
