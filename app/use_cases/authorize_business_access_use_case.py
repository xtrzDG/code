from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)


class AuthorizeBusinessAccessUseCase(
    UseCaseContract[BusinessAccessRequest, BusinessDocument]
):
    """
    Return the business when the user may act on it.

    A business the user is not a member of is reported as missing, not
    forbidden, so foreign ids cannot be probed. Staff asking for an owner-only
    action get AccessDeniedError. Platform admins pass and leave an
    ADMIN_ACCESS entry in the audit log (concept section 8 and 10).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessAccessRequest) -> BusinessDocument:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        for member in business.members:
            if member.user_id != input_data.user_id:
                continue

            if (
                input_data.required_role is BusinessMemberRole.OWNER
                and member.role is not BusinessMemberRole.OWNER
            ):
                raise AccessDeniedError("Only the business owner may do this.")

            return business

        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if user is not None and user.is_platform_admin:
            now: Microseconds = self._wall_clock.now_unix()
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=user.id,
                    action=AuditAction.ADMIN_ACCESS,
                    entity=AuditEntityName("business"),
                    entity_id=AuditEntityReference(str(business.id)),
                    created_at=now,
                    updated_at=now,
                )
            )
            return business

        raise NotFoundError(f"Business {input_data.business_id} was not found.")
