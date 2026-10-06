"""
REST-hook subscriptions of the public API (Zapier): an integration
subscribes its own URL to events and unsubscribes when its Zap is turned
off. Each needs `webhooks:manage`; both are audited with the key's owner.
"""

from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import WebhookPosterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    WebhookEndpointRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.integrations import ApiKeyScope, WebhookEndpointOrigin
from app.schemas.dto.integrations.webhook_views import CreatedWebhookEndpoint
from app.schemas.dto.public_api.access import ApiKeyPrincipal
from app.schemas.dto.public_api.commands import (
    PublicWebhookCommand,
    PublicWebhookRemoval,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.integrations.api_key_records import require_scope
from app.use_cases.integrations.webhook_records import (
    WEBHOOK_ENDPOINT_ENTITY,
    endpoint_view,
    new_endpoint,
    refuse_address,
    refuse_when_full,
    require_endpoint,
)
from app.use_cases.shared.operations_support import build_audit_entry

NOT_SUBSCRIBED_MESSAGE: str = "No webhook of this business was made through the API."


class SubscribePublicWebhookUseCase(
    UseCaseContract[PublicWebhookCommand, CreatedWebhookEndpoint]
):
    """
    A new endpoint made through the API: the same address checks and cap
    as the cabinet's, tied to the key (revoking the key deletes it), its
    signing secret in the answer once.
    """

    def __init__(
        self,
        endpoint_repo: WebhookEndpointRepoContract,
        poster: WebhookPosterContract,
        cipher: SecretCipherAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._poster: WebhookPosterContract = poster
        self._cipher: SecretCipherAdapterContract = cipher
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicWebhookCommand) -> CreatedWebhookEndpoint:
        principal: ApiKeyPrincipal = input_data.principal
        require_scope(principal, ApiKeyScope.WEBHOOKS_MANAGE)
        refusal = self._poster.vet(input_data.request.url)
        if refusal is not None:
            raise refuse_address(refusal)

        refuse_when_full(self._endpoint_repo, principal.business_id)
        now: Microseconds = self._wall_clock.now_unix()
        endpoint, secret = new_endpoint(
            self._cipher,
            principal.business_id,
            input_data.request.url,
            input_data.request.label,
            input_data.request.event_types,
            now,
            created_by=principal.created_by,
            api_key_id=principal.api_key_id,
        )
        self._endpoint_repo.save(endpoint)
        self._audit_log_repo.append(
            build_audit_entry(
                principal.business_id,
                principal.created_by,
                AuditAction.CREATE,
                WEBHOOK_ENDPOINT_ENTITY,
                str(endpoint.id),
                now,
                principal.client_ip_address,
            )
        )
        return CreatedWebhookEndpoint(
            endpoint=endpoint_view(endpoint), signing_secret=secret
        )


class UnsubscribePublicWebhookUseCase(UseCaseContract[PublicWebhookRemoval, None]):
    """
    Delete an endpoint made through the API (by any key of the business:
    a reconnected Zapier account has a new key); the owner's own webhooks
    from the cabinet are not the API's to delete (404).
    """

    def __init__(
        self,
        endpoint_repo: WebhookEndpointRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicWebhookRemoval) -> None:
        principal: ApiKeyPrincipal = input_data.principal
        require_scope(principal, ApiKeyScope.WEBHOOKS_MANAGE)
        endpoint = require_endpoint(
            self._endpoint_repo, principal.business_id, input_data.endpoint_id
        )
        if endpoint.origin is not WebhookEndpointOrigin.API:
            raise NotFoundError(NOT_SUBSCRIBED_MESSAGE)

        self._endpoint_repo.delete(principal.business_id, endpoint.id)
        self._audit_log_repo.append(
            build_audit_entry(
                principal.business_id,
                principal.created_by,
                AuditAction.DELETE,
                WEBHOOK_ENDPOINT_ENTITY,
                str(endpoint.id),
                self._wall_clock.now_unix(),
                principal.client_ip_address,
            )
        )
