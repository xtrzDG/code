from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.contacts import ContactPage
from app.schemas.dto.customers.customer_segments import SegmentMembersQuery
from app.use_cases.contacts.segments.segment_support import (
    CONTACT_ENTITY,
    MemberRows,
    audit_entry,
    authorize_owner,
    require_segment,
)
from app.use_cases.shared.customer_segment_members import (
    SegmentReaders,
    SegmentScan,
    scan_segment,
)


class ListSegmentMembersUseCase(UseCaseContract[SegmentMembersQuery, ContactPage]):
    """
    One page of a segment's customers, the most recently active first,
    computed from its rules now (`customer_segment_members`): a page may
    hold fewer than asked when the walk stopped at its bound, and "Load
    more" goes on. Owners only; personal data, so audited (VIEW of
    contact, the segment named).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        segment_repo: CustomerSegmentRepoContract,
        readers: SegmentReaders,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._segment_repo: CustomerSegmentRepoContract = segment_repo
        self._readers: SegmentReaders = readers
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SegmentMembersQuery) -> ContactPage:
        """
        Raises:
            NotFoundError: no such segment in the business.
            ValidationFailedError: the cursor is broken.
        """

        business: BusinessDocument = authorize_owner(
            self._authorize_business_access, input_data.user_id, input_data.business_id
        )
        segment: CustomerSegmentDocument = require_segment(
            self._segment_repo, business.id, input_data.segment_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        scan: SegmentScan = scan_segment(
            self._readers, business.id, segment.rules, now, input_data.page
        )
        self._audit_log_repo.append(
            audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.VIEW,
                input_data.client_ip_address,
                now,
                entity=CONTACT_ENTITY,
                segment_id=segment.id,
            )
        )
        return ContactPage(
            items=MemberRows(self._readers).summarize(business.id, scan.members),
            next_cursor=scan.next_cursor,
        )
