from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_segments import SegmentExportPageQuery
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.privacy.csv_exports import CsvExportPage
from app.schemas.typings.platform.constrained_integers import PageSize
from app.use_cases.contacts.segments.segment_rows import member_row
from app.use_cases.contacts.segments.segment_support import (
    MemberRows,
    authorize_owner,
    require_segment,
)
from app.use_cases.shared.customer_segment_members import (
    SegmentReaders,
    SegmentScan,
    scan_segment,
)
from app.utilities.scheduling.zoned_time import load_time_zone

EXPORT_PAGE: PageSize = PageSize(200)


class ReadSegmentExportPageUseCase(
    UseCaseContract[SegmentExportPageQuery, CsvExportPage]
):
    """
    One page of a segment's CSV after `cursor`: its members as rows (a page
    can hold none while the walk goes on). Owners only, like starting it.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        segment_repo: CustomerSegmentRepoContract,
        readers: SegmentReaders,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._segment_repo: CustomerSegmentRepoContract = segment_repo
        self._readers: SegmentReaders = readers
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SegmentExportPageQuery) -> CsvExportPage:
        business: BusinessDocument = authorize_owner(
            self._authorize_business_access,
            input_data.user_id,
            input_data.business_id,
            access_mode=BusinessAccessMode.WRITE,
        )
        segment: CustomerSegmentDocument = require_segment(
            self._segment_repo, business.id, input_data.segment_id
        )
        scan: SegmentScan = scan_segment(
            self._readers,
            business.id,
            segment.rules,
            self._wall_clock.now_unix(),
            PageRequest(size=EXPORT_PAGE, cursor=input_data.cursor),
        )
        zone = load_time_zone(business.timezone)
        return CsvExportPage(
            rows=[
                member_row(member, zone)
                for member in MemberRows(self._readers).summarize(
                    business.id, scan.members
                )
            ],
            next_cursor=scan.next_cursor,
        )
