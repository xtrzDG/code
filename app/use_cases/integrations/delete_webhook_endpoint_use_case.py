from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    WebhookEndpointRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.webhook_views import WebhookEndpointCommand
from app.use_cases.integrations.webhook_records import (
    WEBHOOK_ENDPOINT_ENTITY,
    require_endpoint,
)
from app.use_cases.shared.operations_support import build_audit_entry


class DeleteWebhookEndpointUseCase(UseCaseContract[WebhookEndpointCommand, None]):
    """
    The owner removes an endpoint: nothing more is sent to it (deliveries
    still waiting end as failed when their attempt finds it gone); its log
    goes with the 30-day purge. Owners only; audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        endpoint_repo: WebhookEndpointRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WebhookEndpointCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        endpoint = require_endpoint(
            self._endpoint_repo, business.id, input_data.endpoint_id
        )
        self._endpoint_repo.delete(business.id, endpoint.id)
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.DELETE,
                WEBHOOK_ENDPOINT_ENTITY,
                str(endpoint.id),
                self._wall_clock.now_unix(),
                input_data.client_ip_address,
            )
        )
