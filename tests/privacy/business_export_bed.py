"""The full business export use cases over the two-tenant accounts testbed."""

import io
import zipfile
from urllib.parse import parse_qs, urlparse

from typed_time_provider import Microseconds

from app.adapters.exports.encrypted_object_export_archive_storage_adapter import (
    EncryptedObjectExportArchiveStorageAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.export_archives import ExportArchiveStorageContract
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
)
from app.repositories.privacy_repositories import BusinessExportRepository
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.dto.privacy.business_exports import (
    BusinessExportDownload,
    BusinessExportDownloadQuery,
    BusinessExportView,
    StartBusinessExportCommand,
    StartBusinessExportRequest,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.constrained_integers import ExportLinkLifetimeHours
from app.schemas.typings.privacy.constrained_strings import BusinessExportToken
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.exports.business_archive import BusinessArchiveBuilder
from app.use_cases.exports.download_business_export_use_case import (
    DownloadBusinessExportUseCase,
)
from app.use_cases.exports.list_business_exports_use_case import (
    ListBusinessExportsUseCase,
)
from app.use_cases.exports.purge_business_exports_use_case import (
    PurgeBusinessExportsUseCase,
)
from app.use_cases.exports.run_business_export_use_case import (
    RunBusinessExportUseCase,
)
from app.use_cases.exports.start_business_export_use_case import (
    StartBusinessExportUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.privacy.export_link_signer import BusinessExportLinkSigner
from tests.compliance.two_tenants import TwoTenants
from tests.knowledge.website_import.recording_job_queue import RecordingJobQueue
from tests.security.previous_key_fakes import DictObjectStorage

EXPORT_KEY: PlatformSecret = PlatformSecret("test-export-key-0000")


class BusinessExportBed:
    def __init__(
        self,
        tenants: TwoTenants,
        archive_storage: ExportArchiveStorageContract | None = None,
    ) -> None:
        testbed = tenants.testbed
        self.tenants: TwoTenants = tenants
        self.clock = testbed.clock
        self.objects = DictObjectStorage()
        self.queue = RecordingJobQueue()
        self.export_repo = BusinessExportRepository(
            InMemoryDocumentCollectionAdapter(BusinessExportDocument)
        )
        self.signer = BusinessExportLinkSigner(EXPORT_KEY)
        storage = archive_storage or EncryptedObjectExportArchiveStorageAdapter(
            client=self.objects, master_secret=EXPORT_KEY
        )
        wall_clock = testbed.clock.build_wall_clock()
        self.start = StartBusinessExportUseCase(
            authorize_business_access=testbed.authorize_business_access,
            export_repo=self.export_repo,
            job_queue=self.queue,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=wall_clock,
            step_up=testbed.step_up,
            link_signer=self.signer,
        )
        self.list = ListBusinessExportsUseCase(
            authorize_business_access=testbed.authorize_business_access,
            export_repo=self.export_repo,
            wall_clock=wall_clock,
            link_signer=self.signer,
        )
        self.job = RunBusinessExportUseCase(
            business_repo=testbed.business_repo,
            export_repo=self.export_repo,
            archive_builder=BusinessArchiveBuilder(
                contact_repo=testbed.contact_repo,
                conversation_repo=testbed.conversation_repo,
                message_repo=testbed.message_repo,
                call_repo=testbed.call_repo,
                booking_repo=testbed.booking_repo,
                lead_repo=testbed.lead_repo,
                handoff_repo=testbed.handoff_repo,
                resource_repo=ResourceRepository(
                    InMemoryDocumentCollectionAdapter(ResourceDocument)
                ),
                knowledge_item_repo=KnowledgeItemRepository(
                    InMemoryDocumentCollectionAdapter(KnowledgeItemDocument)
                ),
                missed_call_repo=testbed.missed_call_repo,
                feedback_request_repo=testbed.feedback_request_repo,
                audit_log_repo=testbed.audit_log_repo,
                text_resolver=LocalizedTextResolver(),
            ),
            archive_storage=storage,
            wall_clock=wall_clock,
            link_hours=ExportLinkLifetimeHours(24),
        )
        self.download_export = DownloadBusinessExportUseCase(
            business_repo=testbed.business_repo,
            export_repo=self.export_repo,
            archive_storage=storage,
            link_signer=self.signer,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.purge = PurgeBusinessExportsUseCase(
            export_repo=self.export_repo,
            archive_storage=storage,
            wall_clock=wall_clock,
        )

    def ask(
        self, user_id: UserId | None = None, language: str = "en"
    ) -> BusinessExportView:
        return self.start.run(
            StartBusinessExportCommand(
                user_id=self.tenants.owner_id if user_id is None else user_id,
                business_id=self.tenants.business.id,
                request=StartBusinessExportRequest(language=LanguageTag(language)),
                client_ip_address=ClientIpAddress("192.0.2.10"),
            )
        )

    def run_job(self, is_final_attempt: bool = True) -> JobReport:
        queued = self.queue.jobs[-1]
        return self.job.run(
            QueuedJobInput(
                job_id=queued.job_id,
                job_name=queued.name,
                payload=queued.payload,
                business_id=queued.business_id,
                is_final_attempt=is_final_attempt,
            )
        )

    def run_purge(self) -> JobReport:
        return self.purge.run(
            JobTick(
                job_name=JobName("purge_business_exports"),
                scheduled_at=Microseconds(self.clock.nanoseconds // 1000),
            )
        )

    def download(self, path: str) -> BusinessExportDownload:
        parsed = urlparse(path)
        _, _, _, business_id, export_id, _ = parsed.path.split("/")
        return self.download_export.run(
            BusinessExportDownloadQuery(
                business_id=self.tenants.business.id,
                export_id=BusinessExportId(export_id),
                token=BusinessExportToken(parse_qs(parsed.query)["token"][0]),
                client_ip_address=ClientIpAddress("198.51.100.7"),
            )
        )


def read_zip(content: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {name: archive.read(name).decode("utf-8") for name in archive.namelist()}
