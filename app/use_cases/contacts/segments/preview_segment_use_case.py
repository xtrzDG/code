from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.customer_segments import SegmentRules
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_segments import (
    SegmentPreview,
    SegmentPreviewCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.contacts.constrained_integers import SegmentMemberCount
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.contacts.segments.segment_support import (
    CONTACT_ENTITY,
    MemberRows,
    audit_entry,
    authorize_owner,
    rules_of,
)
from app.use_cases.shared.customer_segment_members import (
    SegmentReaders,
    SegmentScan,
    scan_segment,
)

# Customers one count reads at most; beyond, the count says "at least".
COUNT_SCAN_LIMIT: int = 20_000
SAMPLE_SIZE: int = 5
COUNT_PAGE: PageSize = PageSize(100)


class PreviewSegmentUseCase(UseCaseContract[SegmentPreviewCommand, SegmentPreview]):
    """
    How many customers rules hold, and the first few, while the owner
    builds a segment (and for a saved one, sent with its rules). Counts
    up to 20 000 customers read, then "at least". Owners only; the sample
    is personal data, so audited (VIEW of contact).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        readers: SegmentReaders,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._readers: SegmentReaders = readers
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SegmentPreviewCommand) -> SegmentPreview:
        business: BusinessDocument = authorize_owner(
            self._authorize_business_access, input_data.user_id, input_data.business_id
        )
        rules: SegmentRules = rules_of(input_data.rules)
        now: Microseconds = self._wall_clock.now_unix()
        sample: list[ContactDocument] = []
        count: int = 0
        scanned: int = 0
        cursor: PageCursor | None = None
        is_exact: bool = False
        while scanned < COUNT_SCAN_LIMIT:
            scan: SegmentScan = scan_segment(
                self._readers,
                business.id,
                rules,
                now,
                PageRequest(size=COUNT_PAGE, cursor=cursor),
                scan_limit=COUNT_SCAN_LIMIT - scanned,
            )
            count += len(scan.members)
            scanned += scan.scanned
            sample.extend(scan.members[: SAMPLE_SIZE - len(sample)])
            if scan.next_cursor is None:
                is_exact = True
                break

            cursor = scan.next_cursor

        self._audit_log_repo.append(
            audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.VIEW,
                input_data.client_ip_address,
                now,
                entity=CONTACT_ENTITY,
            )
        )
        return SegmentPreview(
            member_count=SegmentMemberCount(count),
            is_count_exact=is_exact,
            sample=MemberRows(self._readers).summarize(business.id, sample),
        )
