from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import WebhookPosterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    WebhookEndpointRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.integrations import WebhookEndpointStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.webhooks import WebhookEndpointDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.webhook_views import (
    UpdateWebhookEndpointCommand,
    WebhookEndpointChange,
    WebhookEndpointView,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.integrations.constrained_integers import WebhookFailureCount
from app.use_cases.integrations.webhook_records import (
    endpoint_view,
    refuse_address,
    require_endpoint,
    subscribed_types,
)
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.integrations.webhook_endpoints import WEBHOOK_ENDPOINT_ENTITY


class UpdateWebhookEndpointUseCase(
    UseCaseContract[UpdateWebhookEndpointCommand, WebhookEndpointView]
):
    """
    The owner changes an endpoint: its address (checked as when it was
    added), note or events, pauses it or switches it on again (an endpoint
    switched off for failures starts counting from zero). Owners only;
    audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        endpoint_repo: WebhookEndpointRepoContract,
        poster: WebhookPosterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._poster: WebhookPosterContract = poster
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateWebhookEndpointCommand) -> WebhookEndpointView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        change: WebhookEndpointChange = input_data.change
        if change.status is WebhookEndpointStatus.DISABLED:
            raise ValidationFailedError("An endpoint is paused or switched on.")

        if change.url is not None:
            refusal = self._poster.vet(change.url)
            if refusal is not None:
                raise refuse_address(refusal)

        require_endpoint(self._endpoint_repo, business.id, input_data.endpoint_id)
        now: Microseconds = self._wall_clock.now_unix()
        stored = self._endpoint_repo.update(
            business.id,
            input_data.endpoint_id,
            lambda current: changed(current, change, now),
        )
        if stored is None:
            raise NotFoundError("This webhook does not exist (any more).")

        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.UPDATE,
                WEBHOOK_ENDPOINT_ENTITY,
                str(stored.id),
                now,
                input_data.client_ip_address,
            )
        )
        return endpoint_view(stored)


def changed(
    current: WebhookEndpointDocument, change: WebhookEndpointChange, now: Microseconds
) -> WebhookEndpointDocument:
    """The endpoint as stored now with the change applied."""

    update: dict[str, object] = {"updated_at": now}
    if change.url is not None:
        update["url"] = change.url
    if change.label is not None:
        update["label"] = change.label
    if change.event_types is not None:
        update["event_types"] = subscribed_types(change.event_types)
    if change.status is not None and change.status is not current.status:
        update["status"] = change.status
        if change.status is WebhookEndpointStatus.ACTIVE:
            update["consecutive_failures"] = WebhookFailureCount(0)
            update["disabled_at"] = None

    return current.model_copy(update=update)
