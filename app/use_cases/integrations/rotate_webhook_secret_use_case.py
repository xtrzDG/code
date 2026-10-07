from typed_time_provider import Microseconds, WallClock

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
    WebhookEndpointCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.integrations.webhook_records import (
    endpoint_view,
)
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.integrations.integration_secrets import new_signing_secret
from app.utilities.integrations.webhook_endpoints import WEBHOOK_ENDPOINT_ENTITY


class RotateWebhookSecretUseCase(
    UseCaseContract[WebhookEndpointCommand, CreatedWebhookEndpoint]
):
    """
    The owner gives an endpoint a new signing secret (a leaked one, a new
    receiver): every request from now on is signed with it, and it is
    shown this once. Owners only; audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        endpoint_repo: WebhookEndpointRepoContract,
        cipher: SecretCipherAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._cipher: SecretCipherAdapterContract = cipher
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WebhookEndpointCommand) -> CreatedWebhookEndpoint:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        secret, hint = new_signing_secret()
        sealed = self._cipher.encrypt(ChannelSecret(str(secret)))
        now: Microseconds = self._wall_clock.now_unix()
        stored = self._endpoint_repo.update(
            business.id,
            input_data.endpoint_id,
            lambda current: current.model_copy(
                update={
                    "encrypted_secret": sealed,
                    "secret_hint": hint,
                    "updated_at": now,
                }
            ),
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
        return CreatedWebhookEndpoint(
            endpoint=endpoint_view(stored), signing_secret=secret
        )
