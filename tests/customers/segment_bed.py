"""The segment use cases over the customer bed, and short ways to call them."""

from app.contracts.session_assurance import StepUpGuardContract
from app.schemas.dto.contacts import ContactPage
from app.schemas.dto.customers.customer_segments import (
    CreateSegmentCommand,
    SegmentExportPageQuery,
    SegmentMembersQuery,
    SegmentPreview,
    SegmentPreviewCommand,
    SegmentRequest,
    SegmentRulesBody,
    SegmentView,
    StartSegmentExportCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.privacy.csv_exports import CsvExportHeader, CsvExportPage
from app.schemas.typings.contacts.constrained_strings import SegmentName
from app.schemas.typings.contacts.prefixed_id import CustomerSegmentId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.contacts.segments.create_segment_use_case import (
    CreateSegmentUseCase,
)
from app.use_cases.contacts.segments.delete_segment_use_case import (
    DeleteSegmentUseCase,
)
from app.use_cases.contacts.segments.list_segment_members_use_case import (
    ListSegmentMembersUseCase,
)
from app.use_cases.contacts.segments.list_segments_use_case import ListSegmentsUseCase
from app.use_cases.contacts.segments.preview_segment_use_case import (
    PreviewSegmentUseCase,
)
from app.use_cases.contacts.segments.read_segment_export_page_use_case import (
    ReadSegmentExportPageUseCase,
)
from app.use_cases.contacts.segments.start_segment_export_use_case import (
    StartSegmentExportUseCase,
)
from app.use_cases.contacts.segments.update_segment_use_case import (
    UpdateSegmentUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.compliance.customer_records import Customers
from tests.customers.customer_bed import CLIENT_IP, CustomerBed


class SegmentBed(CustomerBed):
    """Saved segments, their members, the preview and the CSV."""

    def __init__(
        self,
        customers: Customers | None = None,
        step_up: StepUpGuardContract | None = None,
    ) -> None:
        super().__init__(customers)
        testbed = self.customers.testbed
        wall_clock = testbed.clock.build_wall_clock()
        authorize = testbed.authorize_business_access
        repo = testbed.customer_segment_repo
        audit = testbed.audit_log_repo
        self.list_segments = ListSegmentsUseCase(
            authorize_business_access=authorize,
            segment_repo=repo,
            customer_settings_repo=testbed.customer_settings_repo,
        )
        self.create_segment = CreateSegmentUseCase(
            authorize_business_access=authorize,
            segment_repo=repo,
            audit_log_repo=audit,
            wall_clock=wall_clock,
        )
        self.update_segment = UpdateSegmentUseCase(
            authorize_business_access=authorize,
            segment_repo=repo,
            audit_log_repo=audit,
            wall_clock=wall_clock,
        )
        self.delete_segment = DeleteSegmentUseCase(
            authorize_business_access=authorize,
            segment_repo=repo,
            audit_log_repo=audit,
            wall_clock=wall_clock,
        )
        self.list_members = ListSegmentMembersUseCase(
            authorize_business_access=authorize,
            segment_repo=repo,
            readers=self.readers,
            audit_log_repo=audit,
            wall_clock=wall_clock,
        )
        self.preview_segment = PreviewSegmentUseCase(
            authorize_business_access=authorize,
            readers=self.readers,
            audit_log_repo=audit,
            wall_clock=wall_clock,
        )
        self.start_export = StartSegmentExportUseCase(
            authorize_business_access=authorize,
            segment_repo=repo,
            audit_log_repo=audit,
            wall_clock=wall_clock,
            step_up=step_up or testbed.step_up,
            text_resolver=LocalizedTextResolver(),
        )
        self.read_export = ReadSegmentExportPageUseCase(
            authorize_business_access=authorize,
            segment_repo=repo,
            readers=self.readers,
            wall_clock=wall_clock,
        )

    def create(
        self,
        name: str,
        rules: SegmentRulesBody,
        user_id: UserId | None = None,
    ) -> SegmentView:
        return self.create_segment.run(
            CreateSegmentCommand(
                user_id=user_id or self.owner_id,
                business_id=self.customers.business.id,
                request=SegmentRequest(name=SegmentName(name), rules=rules),
                client_ip_address=CLIENT_IP,
            )
        )

    def members(
        self, segment_id: CustomerSegmentId, page: PageRequest | None = None
    ) -> ContactPage:
        return self.list_members.run(
            SegmentMembersQuery(
                user_id=self.owner_id,
                business_id=self.customers.business.id,
                segment_id=segment_id,
                page=page or PageRequest(),
                client_ip_address=CLIENT_IP,
            )
        )

    def preview(self, rules: SegmentRulesBody) -> SegmentPreview:
        return self.preview_segment.run(
            SegmentPreviewCommand(
                user_id=self.owner_id,
                business_id=self.customers.business.id,
                rules=rules,
                client_ip_address=CLIENT_IP,
            )
        )

    def export_header(
        self, segment_id: CustomerSegmentId, language: str = "en"
    ) -> CsvExportHeader:
        return self.start_export.run(
            StartSegmentExportCommand(
                user_id=self.owner_id,
                business_id=self.customers.business.id,
                segment_id=segment_id,
                language=LanguageTag(language),
                client_ip_address=CLIENT_IP,
            )
        )

    def export_page(
        self, segment_id: CustomerSegmentId, cursor: PageCursor | None = None
    ) -> CsvExportPage:
        return self.read_export.run(
            SegmentExportPageQuery(
                user_id=self.owner_id,
                business_id=self.customers.business.id,
                segment_id=segment_id,
                cursor=cursor,
            )
        )
