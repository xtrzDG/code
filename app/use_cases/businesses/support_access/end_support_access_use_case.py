from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import SupportAccessEndReason
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.support_access import (
    EndSupportAccessCommand,
    SupportAccessEnding,
)
from app.use_cases.businesses.support_access.support_access_views import (
    require_owner_member,
)
from app.use_cases.shared.support_access import end_grant, is_live


class EndSupportAccessUseCase(UseCaseContract[EndSupportAccessCommand, None]):
    """
    The owner ends platform support's access at once (the banner's "End
    access"): every open look into the cabinet (SUPPORT_ACCESS_END) and the
    consent to changes. Support's next request is refused.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        grant_repo: SupportAccessGrantRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._grant_repo: SupportAccessGrantRepoContract = grant_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: EndSupportAccessCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        require_owner_member(business, input_data.user_id)
        now: Microseconds = self._wall_clock.now_unix()
        for grant in self._grant_repo.list_open(business.id):
            if is_live(grant, now):
                end_grant(
                    self._grant_repo,
                    self._audit_log_repo,
                    grant,
                    SupportAccessEnding(
                        ended_at=now,
                        ended_by=input_data.user_id,
                        reason=SupportAccessEndReason.REVOKED_BY_OWNER,
                    ),
                    input_data.client_ip_address,
                )
