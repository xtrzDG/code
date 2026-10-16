from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.spend_guard_repositories import (
    BusinessLimitsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.business_limits import BusinessLimitsDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.spend_guard import (
    BusinessSpendLimitsCommand,
    BusinessSpendLimitsView,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)

AUDITED_ENTITY: AuditEntityName = AuditEntityName("spend_limits")


class SetBusinessSpendLimitsUseCase(
    UseCaseContract[BusinessSpendLimitsCommand, BusinessSpendLimitsView]
):
    """
    A platform admin sets a client's own daily spend limits (null: back to
    the plan's default), for a client whose traffic is legitimately high or
    to brake one at once (a hard limit of 0 stops its model until it is
    raised). Written to the client's audit log (UPDATE, by the admin).

    Raises:
        ValidationFailedError: a soft limit above the hard one.
        NotFoundError: no such business.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        business_limits_repo: BusinessLimitsRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._limits_repo: BusinessLimitsRepoContract = business_limits_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessSpendLimitsCommand) -> BusinessSpendLimitsView:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        soft, hard = (
            input_data.request.soft_limit_micro_usd,
            input_data.request.hard_limit_micro_usd,
        )
        if soft is not None and hard is not None and int(soft) > int(hard):
            raise ValidationFailedError(
                "The soft limit must not be above the hard one."
            )

        now: Microseconds = self._wall_clock.now_unix()
        limits: BusinessLimitsDocument = self._limits_repo.get_or_default(business.id)
        limits.daily_soft_limit_micro_usd = soft
        limits.daily_hard_limit_micro_usd = hard
        limits.updated_at = now
        self._limits_repo.save(limits)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=admin.id,
                action=AuditAction.UPDATE,
                entity=AUDITED_ENTITY,
                entity_id=AuditEntityReference(str(limits.id)),
                created_at=now,
                updated_at=now,
            )
        )
        return BusinessSpendLimitsView(
            business_id=business.id,
            soft_limit_micro_usd=limits.daily_soft_limit_micro_usd,
            hard_limit_micro_usd=limits.daily_hard_limit_micro_usd,
        )
