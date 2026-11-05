from app.contracts.repositories.audit_chain_repositories import (
    AuditChainRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditChainStatus
from app.schemas.domain.users import UserDocument
from app.schemas.dto.audit_chain_views import (
    AdminAuditChainsQuery,
    AuditChainOverview,
    BrokenAuditChainView,
)
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.compliance.constrained_integers import AuditChainCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.shared.audit_chain_views import read_chain_status
from app.utilities.compliance.audit_chain_hashing import (
    PLATFORM_CHAIN_KEY,
    business_of_chain,
)

BROKEN_SHOWN: DocumentQueryLimit = DocumentQueryLimit(50)


class GetAuditChainOverviewUseCase(
    UseCaseContract[AdminAuditChainsQuery, AuditChainOverview]
):
    """
    The platform admin's view of the audit log's integrity: the platform's
    own chain, how many chains the latest daily checks found intact and
    broken (counted by the database), and the broken ones.

    Raises:
        AccessDeniedError: the user may not see the platform's operations.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        audit_chain_repo: AuditChainRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._audit_chain_repo: AuditChainRepoContract = audit_chain_repo

    def run(self, input_data: AdminAuditChainsQuery) -> AuditChainOverview:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        counts = self._audit_chain_repo.count_by_status()
        return AuditChainOverview(
            platform=read_chain_status(self._audit_chain_repo, PLATFORM_CHAIN_KEY),
            intact_chains=AuditChainCount(int(counts[AuditChainStatus.INTACT])),
            broken_chains=AuditChainCount(int(counts[AuditChainStatus.BROKEN])),
            broken=[
                BrokenAuditChainView(
                    business_id=business_of_chain(status.id),
                    problem=status.problem,
                    broken_position=status.broken_position,
                    checked_at=status.checked_at,
                )
                for status in self._audit_chain_repo.list_broken(BROKEN_SHOWN)
            ],
        )
