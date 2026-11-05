from app.contracts.repositories.audit_chain_repositories import (
    AuditChainRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.audit_chain_views import (
    AuditChainStatusQuery,
    AuditChainStatusView,
)
from app.use_cases.shared.audit_chain_views import read_chain_status
from app.utilities.compliance.audit_chain_hashing import chain_key_of


class GetAuditChainStatusUseCase(
    UseCaseContract[AuditChainStatusQuery, AuditChainStatusView]
):
    """
    The owner's view of the audit log's integrity: how the latest daily
    check of the business's hash chain went (intact through which entry,
    or broken where and why) and where a purge last cut it.

    Raises:
        NotFoundError: the business is not the user's.
        AccessDeniedError: the user is staff, not an owner.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        audit_chain_repo: AuditChainRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._audit_chain_repo: AuditChainRepoContract = audit_chain_repo

    def run(self, input_data: AuditChainStatusQuery) -> AuditChainStatusView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return read_chain_status(self._audit_chain_repo, chain_key_of(business.id))
