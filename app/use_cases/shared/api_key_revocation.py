"""
Revoking a business's API key: it stops working at once (its next request
is 401) and stays listed as revoked, and the webhooks it subscribed
(Zapier's REST hooks) are deleted with it, since nothing would unsubscribe
them. Revoking twice changes nothing. Each revocation is audited (DELETE
of the `api_key`). Used by Settings → Integrations and by the removal of a
team member, whose keys leave with them.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    ApiKeyRepoContract,
    WebhookEndpointRepoContract,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.integrations import ApiKeyStatus
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName, ClientIpAddress
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.operations_support import build_audit_entry

API_KEY_ENTITY: AuditEntityName = AuditEntityName("api_key")


class ApiKeyRevocation:
    """Revokes keys of one business on behalf of one person, at one moment."""

    def __init__(
        self,
        api_key_repo: ApiKeyRepoContract,
        endpoint_repo: WebhookEndpointRepoContract,
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._api_key_repo: ApiKeyRepoContract = api_key_repo
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def revoke(
        self,
        business_id: BusinessId,
        api_key_id: ApiKeyId,
        actor_id: UserId,
        now: Microseconds,
        client_ip_address: ClientIpAddress | None,
    ) -> bool:
        """True when this call revoked the key (False: revoked before)."""

        def revoked(stored: ApiKeyDocument) -> ApiKeyDocument | None:
            if stored.status is ApiKeyStatus.REVOKED:
                return None

            return stored.model_copy(
                update={
                    "status": ApiKeyStatus.REVOKED,
                    "revoked_at": now,
                    "revoked_by": actor_id,
                    "updated_at": now,
                }
            )

        if self._api_key_repo.update(business_id, api_key_id, revoked) is None:
            return False

        for endpoint in self._endpoint_repo.list_by_business(business_id):
            if endpoint.api_key_id == api_key_id:
                self._endpoint_repo.delete(business_id, endpoint.id)
        self._audit_log_repo.append(
            build_audit_entry(
                business_id,
                actor_id,
                AuditAction.DELETE,
                API_KEY_ENTITY,
                str(api_key_id),
                now,
                client_ip_address,
            )
        )
        return True

    def revoke_created_by(
        self,
        business_id: BusinessId,
        creator_id: UserId,
        actor_id: UserId,
        now: Microseconds,
        client_ip_address: ClientIpAddress | None,
    ) -> list[ApiKeyId]:
        """Every active key `creator_id` made in the business; the revoked ones."""

        return [
            api_key.id
            for api_key in self._api_key_repo.list_by_business(business_id)
            if api_key.created_by == creator_id
            and api_key.status is ApiKeyStatus.ACTIVE
            and self.revoke(business_id, api_key.id, actor_id, now, client_ip_address)
        ]
