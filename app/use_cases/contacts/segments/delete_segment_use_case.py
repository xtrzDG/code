from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_segments import SegmentQuery
from app.use_cases.contacts.segments.segment_support import (
    audit_entry,
    authorize_owner,
    require_segment,
)


class DeleteSegmentUseCase(UseCaseContract[SegmentQuery, None]):
    """The owner deletes a segment (its customers stay). Audited (DELETE)."""

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        segment_repo: CustomerSegmentRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._segment_repo: CustomerSegmentRepoContract = segment_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SegmentQuery) -> None:
        """
        Raises:
            NotFoundError: no such segment in the business.
        """

        business: BusinessDocument = authorize_owner(
            self._authorize_business_access, input_data.user_id, input_data.business_id
        )
        require_segment(self._segment_repo, business.id, input_data.segment_id)
        self._segment_repo.delete(business.id, input_data.segment_id)
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.DELETE,
                input_data.client_ip_address,
                now,
                segment_id=input_data.segment_id,
            )
        )
