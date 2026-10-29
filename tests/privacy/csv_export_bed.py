"""The CSV export use cases over the two-tenant accounts testbed."""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.gateways.http.csv_streaming import stream_csv
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
)
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.privacy.csv_exports import (
    CsvExportFilters,
    CsvExportHeader,
    CsvExportPage,
    CsvExportPageQuery,
    StartCsvExportCommand,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.exports.read_csv_export_page_use_case import (
    ReadCsvExportPageUseCase,
)
from app.use_cases.exports.start_csv_export_use_case import StartCsvExportUseCase
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.compliance.two_tenants import TwoTenants


class CsvExportBed:
    def __init__(
        self,
        tenants: TwoTenants,
        audit_log_repo: AuditLogRepoContract | None = None,
    ) -> None:
        testbed = tenants.testbed
        self.tenants: TwoTenants = tenants
        self.start = StartCsvExportUseCase(
            authorize_business_access=testbed.authorize_business_access,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=testbed.clock.build_wall_clock(),
            step_up=testbed.step_up,
            text_resolver=LocalizedTextResolver(),
        )
        self.read = ReadCsvExportPageUseCase(
            authorize_business_access=testbed.authorize_business_access,
            booking_repo=testbed.booking_repo,
            resource_repo=ResourceRepository(
                InMemoryDocumentCollectionAdapter(ResourceDocument)
            ),
            knowledge_item_repo=KnowledgeItemRepository(
                InMemoryDocumentCollectionAdapter(KnowledgeItemDocument)
            ),
            lead_repo=testbed.lead_repo,
            contact_repo=testbed.contact_repo,
            conversation_repo=testbed.conversation_repo,
            message_repo=testbed.message_repo,
            audit_log_repo=audit_log_repo or testbed.audit_log_repo,
            phone_number_parser=testbed.phone_parser,
        )

    def header(
        self,
        kind: CsvExportKind,
        language: str = "en",
        user_id: UserId | None = None,
    ) -> CsvExportHeader:
        return self.start.run(
            StartCsvExportCommand(
                user_id=self.tenants.owner_id if user_id is None else user_id,
                business_id=self.tenants.business.id,
                kind=kind,
                language=LanguageTag(language),
                client_ip_address=ClientIpAddress("192.0.2.10"),
            )
        )

    def page(
        self,
        kind: CsvExportKind,
        filters: CsvExportFilters | None = None,
        cursor: PageCursor | None = None,
        user_id: UserId | None = None,
    ) -> CsvExportPage:
        return self.read.run(
            CsvExportPageQuery(
                user_id=self.tenants.owner_id if user_id is None else user_id,
                business_id=self.tenants.business.id,
                kind=kind,
                filters=filters or CsvExportFilters(),
                cursor=cursor,
            )
        )

    def csv(
        self,
        kind: CsvExportKind,
        filters: CsvExportFilters | None = None,
        language: str = "en",
    ) -> str:
        """The whole download as the browser receives it."""

        chunks = stream_csv(
            self.header(kind, language),
            lambda cursor: self.page(kind, filters, cursor),
        )
        return b"".join(chunks).decode("utf-8")
