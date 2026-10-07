from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.webhook_views import (
    WebhookDeliveryCommand,
    WebhookDeliveryDetail,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.integrations.webhook_records import (
    WEBHOOK_DELIVERY_ENTITY,
    delivery_view,
)
from app.use_cases.shared.operations_support import build_audit_entry


class GetWebhookDeliveryUseCase(
    UseCaseContract[WebhookDeliveryCommand, WebhookDeliveryDetail]
):
    """
    One delivery with the exact body it sends, which names the customer:
    the view is audited. Owners only.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        delivery_repo: WebhookDeliveryRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._delivery_repo: WebhookDeliveryRepoContract = delivery_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WebhookDeliveryCommand) -> WebhookDeliveryDetail:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        delivery = self._delivery_repo.get(business.id, input_data.delivery_id)
        if delivery is None:
            raise NotFoundError("This delivery does not exist (any more).")

        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.VIEW,
                WEBHOOK_DELIVERY_ENTITY,
                str(delivery.id),
                self._wall_clock.now_unix(),
                input_data.client_ip_address,
            )
        )
        return WebhookDeliveryDetail(
            delivery=delivery_view(delivery), payload=delivery.payload
        )
