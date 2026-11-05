from datetime import UTC, datetime

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_segments import StartSegmentExportCommand
from app.schemas.dto.privacy.csv_exports import CsvExportHeader
from app.schemas.typings.privacy.constrained_strings import ExportFileName
from app.schemas.typings.privacy.strings import CsvColumnTitle
from app.use_cases.contacts.segments.segment_support import (
    audit_entry,
    authorize_owner,
    require_segment,
)
from app.utilities.customers.segment_csv_columns import SEGMENT_CSV_COLUMNS
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000


class StartSegmentExportUseCase(
    UseCaseContract[StartSegmentExportCommand, CsvExportHeader]
):
    """
    The owner downloads a segment's customers as CSV (for a campaign
    elsewhere). Personal data leaves the platform: owners only (never
    staff or read-only support), after a recent sign-in or step-up, audited
    once (EXPORT of customer_segment, the segment named) before any row is
    read. Returns the file name and the headings in the owner's language;
    the rows follow a page at a time (ReadSegmentExportPageUseCase).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        segment_repo: CustomerSegmentRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
        text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._segment_repo: CustomerSegmentRepoContract = segment_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def run(self, input_data: StartSegmentExportCommand) -> CsvExportHeader:
        """
        Raises:
            NotFoundError: no such segment in the business.
            StepUpRequiredError: the session must prove its person again.
        """

        business: BusinessDocument = authorize_owner(
            self._authorize_business_access,
            input_data.user_id,
            input_data.business_id,
            access_mode=BusinessAccessMode.WRITE,
        )
        segment: CustomerSegmentDocument = require_segment(
            self._segment_repo, business.id, input_data.segment_id
        )
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.EXPORT,
                input_data.client_ip_address,
                now,
                segment_id=segment.id,
            )
        )
        local_day: str = (
            datetime.fromtimestamp(int(now) / MICROSECONDS_PER_SECOND, tz=UTC)
            .astimezone(load_time_zone(business.timezone))
            .date()
            .isoformat()
        )
        return CsvExportHeader(
            file_name=ExportFileName(f"segment-{local_day}.csv"),
            columns=[
                CsvColumnTitle(
                    str(self._text_resolver.resolve(title, input_data.language))
                )
                for title in SEGMENT_CSV_COLUMNS
            ],
        )
