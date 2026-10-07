from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import WebhookPosterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    WebhookEndpointRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.webhook_views import (
    CreatedWebhookEndpoint,
    CreateWebhookEndpointCommand,
)
from app.use_cases.integrations.webhook_records import (
    WEBHOOK_ENDPOINT_ENTITY,
    endpoint_view,
    new_endpoint,
    refuse_address,
    refuse_when_full,
)
from app.use_cases.shared.operations_support import build_audit_entry


class CreateWebhookEndpointUseCase(
    UseCaseContract[CreateWebhookEndpointCommand, CreatedWebhookEndpoint]
):
    """
    The owner adds an address events are sent to. It must be a public
    https address (the SSRF guard's checks before any lookup; its host is
    checked again on every delivery), the business may have at most ten,
    and its signing secret is made here, sealed, and shown this once.
    Owners only; audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        endpoint_repo: WebhookEndpointRepoContract,
        poster: WebhookPosterContract,
        cipher: SecretCipherAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._poster: WebhookPosterContract = poster
        self._cipher: SecretCipherAdapterContract = cipher
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateWebhookEndpointCommand) -> CreatedWebhookEndpoint:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        refusal = self._poster.vet(input_data.request.url)
        if refusal is not None:
            raise refuse_address(refusal)

        refuse_when_full(self._endpoint_repo, business.id)
        now: Microseconds = self._wall_clock.now_unix()
        endpoint, secret = new_endpoint(
            self._cipher,
            business.id,
            input_data.request.url,
            input_data.request.label,
            input_data.request.event_types,
            now,
            created_by=input_data.user_id,
        )
        self._endpoint_repo.save(endpoint)
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.CREATE,
                WEBHOOK_ENDPOINT_ENTITY,
                str(endpoint.id),
                now,
                input_data.client_ip_address,
            )
        )
        return CreatedWebhookEndpoint(
            endpoint=endpoint_view(endpoint), signing_secret=secret
        )
