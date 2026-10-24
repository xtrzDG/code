from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    ApiKeyRepoContract,
    WebhookEndpointRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.integrations import ApiKeyStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.api_key_views import ApiKeyCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.integrations.api_key_records import API_KEY_ENTITY
from app.use_cases.shared.operations_support import build_audit_entry

UNKNOWN_KEY_MESSAGE: str = "API key not found."


class RevokeApiKeyUseCase(UseCaseContract[ApiKeyCommand, None]):
    """
    Revoke a key: it stops working at once (its next request is 401) and
    stays listed as revoked; the webhooks it subscribed (Zapier's REST
    hooks) are deleted with it, since nothing would unsubscribe them.
    Revoking twice changes nothing. Owners only; audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        api_key_repo: ApiKeyRepoContract,
        endpoint_repo: WebhookEndpointRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._api_key_repo: ApiKeyRepoContract = api_key_repo
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ApiKeyCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        if self._api_key_repo.get(business.id, input_data.api_key_id) is None:
            raise NotFoundError(UNKNOWN_KEY_MESSAGE)

        now: Microseconds = self._wall_clock.now_unix()

        def revoke(stored: ApiKeyDocument) -> ApiKeyDocument | None:
            if stored.status is ApiKeyStatus.REVOKED:
                return None

            return stored.model_copy(
                update={
                    "status": ApiKeyStatus.REVOKED,
                    "revoked_at": now,
                    "revoked_by": input_data.user_id,
                    "updated_at": now,
                }
            )

        if (
            self._api_key_repo.update(business.id, input_data.api_key_id, revoke)
            is None
        ):
            return

        for endpoint in self._endpoint_repo.list_by_business(business.id):
            if endpoint.api_key_id == input_data.api_key_id:
                self._endpoint_repo.delete(business.id, endpoint.id)
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.DELETE,
                API_KEY_ENTITY,
                str(input_data.api_key_id),
                now,
                input_data.client_ip_address,
            )
        )
