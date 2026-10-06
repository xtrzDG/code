"""The platform admin behind a partner action, and the audit entry it leaves."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.referral_repositories import PartnerRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.schemas.typings.users.prefixed_id import UserId

PARTNER_ENTITY: AuditEntityName = AuditEntityName("partner")
PARTNER_CODE_ENTITY: AuditEntityName = AuditEntityName("partner_code")
PARTNER_PAYOUT_ENTITY: AuditEntityName = AuditEntityName("partner_payout")


class PartnerAdminGate:
    """
    Partner actions are the platform team's: viewing needs VIEW_CLIENTS,
    changing a partner or paying them out MANAGE_CLIENT_BILLING. A change
    leaves a platform audit entry (no business) naming the admin, the
    partner and the request's address: partners are people, and payouts
    are money.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        partner_repo: PartnerRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._partner_repo: PartnerRepoContract = partner_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def admit(
        self, user_id: UserId, permission: PlatformAdminPermission
    ) -> UserDocument:
        return self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(user_id=user_id, permission=permission)
        )

    def require_partner(self, partner_id: PartnerId) -> PartnerDocument:
        partner: PartnerDocument | None = self._partner_repo.get(partner_id)
        if partner is None:
            raise NotFoundError(f"Partner {partner_id} was not found.")

        return partner

    def now(self) -> Microseconds:
        return self._wall_clock.now_unix()

    def record(
        self,
        admin: UserDocument,
        action: AuditAction,
        entity: AuditEntityName,
        partner_id: PartnerId,
        client_ip_address: ClientIpAddress | None,
        record_count: int | None = None,
    ) -> None:
        now: Microseconds = self.now()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                actor_id=admin.id,
                action=action,
                entity=entity,
                entity_id=AuditEntityReference(str(partner_id)),
                ip_address=client_ip_address,
                record_count=(
                    None if record_count is None else AuditRecordCount(record_count)
                ),
                created_at=now,
                updated_at=now,
            )
        )
