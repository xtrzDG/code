from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    ApiKeyRepoContract,
    WebhookEndpointRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.api_key_views import ApiKeyCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.shared.api_key_revocation import ApiKeyRevocation

UNKNOWN_KEY_MESSAGE: str = "API key not found."


class RevokeApiKeyUseCase(UseCaseContract[ApiKeyCommand, None]):
    """
    Revoke a key: it stops working at once (its next request is 401) and
    stays listed as revoked; the webhooks it subscribed (Zapier's REST
    hooks) are deleted with it, since nothing would unsubscribe them.
    Revoking twice changes nothing. Owners only; audited
    (ApiKeyRevocation). Revoking needs no fresh confirmation: closing a
    door is never slowed down.
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
        self._revocation: ApiKeyRevocation = ApiKeyRevocation(
            api_key_repo, endpoint_repo, audit_log_repo
        )
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

        self._revocation.revoke(
            business.id,
            input_data.api_key_id,
            input_data.user_id,
            self._wall_clock.now_unix(),
            input_data.client_ip_address,
        )
