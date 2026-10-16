"""
The archive of a full business export: a ZIP with a JSON file per
collection of the business's data and the cabinet's tables as CSV (the
same rows as their downloads), with a README. Erased customers are left
out; secrets never leave (channel credentials are not exported at all,
review link tokens are dropped).

The archive is written into a file (the worker's temporary file), each
collection streamed in keyset pages of 1,000 through incremental JSON and
CSV writers: the worker holds a page, never a collection, however large
the business's history.
"""

import zipfile
from dataclasses import dataclass
from typing import IO
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import (
    LocalizedTextResolverContract,
    PhoneNumberParserContract,
)
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.call_follow_up_repositories import (
    MissedCallRepoContract,
)
from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.privacy.constrained_integers import ExportedRecordCount
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.exports.archive_pages import (
    DocumentPages,
    conversation_pages,
    customer_pages,
    pages_in_write_order,
    single_page,
)
from app.use_cases.exports.archive_tables import ArchiveTables
from app.use_cases.exports.archive_writers import write_csv_table, write_json_array
from app.use_cases.exports.business_rows import BookingRows, LeadRows
from app.use_cases.exports.growth_archive import growth_pages
from app.use_cases.exports.people_rows import AuditRows, ContactRows, ConversationRows
from app.utilities.privacy.csv_cells import moment_cell
from app.utilities.privacy.csv_columns import CSV_COLUMNS
from app.utilities.scheduling.zoned_time import load_time_zone

README: str = """Full export of {business}, made {made_at} ({timezone}).

JSON: one file per kind of record, as the platform keeps them (times are
UTC microseconds since 1970). CSV: the cabinet's tables, as their
downloads (local times, UTF-8). Customers who asked to be erased are not
in it; channel credentials and review link tokens never leave the
platform.
"""


@dataclass(frozen=True)
class BusinessArchiveBuilder:
    contact_repo: ContactRepoContract
    conversation_repo: ConversationTeamRepoContract
    message_repo: MessageRepoContract
    call_repo: CallRepoContract
    booking_repo: BookingRepoContract
    lead_repo: LeadRepoContract
    handoff_repo: HandoffRepoContract
    resource_repo: ResourceRepoContract
    knowledge_item_repo: KnowledgeItemRepoContract
    missed_call_repo: MissedCallRepoContract
    feedback_request_repo: FeedbackRequestRepoContract
    audit_log_repo: AuditLogRepoContract
    text_resolver: LocalizedTextResolverContract
    phone_number_parser: PhoneNumberParserContract
    waitlist_entry_repo: WaitlistEntryRepoContract | None = None
    campaign_message_repo: CampaignMessageRepoContract | None = None

    def write(
        self,
        business: BusinessDocument,
        language: LanguageTag,
        now: Microseconds,
        viewer: UserId,
        target: IO[bytes],
    ) -> ExportedRecordCount:
        """
        Write the archive into `target` (a file open for writing); how many
        records its JSON files hold. `viewer` is who reads the tables (the
        owner who asked).
        """

        zone: ZoneInfo = load_time_zone(business.timezone)
        records: int = 0
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "README.txt",
                README.format(
                    business=business.name,
                    made_at=str(moment_cell(now, zone)),
                    timezone=business.timezone,
                ),
            )
            for name, pages in self._collections(business).items():
                with archive.open(f"{name}.json", "w", force_zip64=True) as stream:
                    records += write_json_array(stream, pages)
            tables = self._tables()
            for kind in CSV_COLUMNS:
                header: list[str] = [
                    str(self.text_resolver.resolve(title, language))
                    for title in CSV_COLUMNS[kind]
                ]
                with archive.open(
                    f"csv/{kind.value}.csv", "w", force_zip64=True
                ) as stream:
                    write_csv_table(
                        stream, header, tables.pages(kind, business, zone, viewer)
                    )

        return ExportedRecordCount(records)

    def _collections(self, business: BusinessDocument) -> dict[str, DocumentPages]:
        """Each JSON file's documents, as pages read when the file is written."""

        return self._business_collections(business) | growth_pages(
            business.id, self.waitlist_entry_repo, self.campaign_message_repo
        )

    def _business_collections(
        self, business: BusinessDocument
    ) -> dict[str, DocumentPages]:
        """The business, its customers and conversations, bookings and log."""

        business_id = business.id
        return {
            "business": single_page([business]),
            "contacts": customer_pages(self.contact_repo, business_id),
            "conversations": conversation_pages(
                self.conversation_repo, self.contact_repo, business_id
            ),
            "messages": pages_in_write_order(
                self.message_repo, business_id, lambda item: str(item.id)
            ),
            "calls": pages_in_write_order(
                self.call_repo, business_id, lambda item: str(item.id)
            ),
            "bookings": pages_in_write_order(
                self.booking_repo, business_id, lambda item: str(item.id)
            ),
            "leads": pages_in_write_order(
                self.lead_repo, business_id, lambda item: str(item.id)
            ),
            "handoffs": pages_in_write_order(
                self.handoff_repo, business_id, lambda item: str(item.id)
            ),
            "resources": single_page(self.resource_repo.list_by_business(business_id)),
            "knowledge_items": pages_in_write_order(
                self.knowledge_item_repo, business_id, lambda item: str(item.id)
            ),
            "missed_calls": pages_in_write_order(
                self.missed_call_repo, business_id, lambda item: str(item.id)
            ),
            "feedback_requests": pages_in_write_order(
                self.feedback_request_repo, business_id, lambda item: str(item.id)
            ),
            "audit_log": pages_in_write_order(
                self.audit_log_repo, business_id, lambda item: str(item.id)
            ),
        }

    def _tables(self) -> ArchiveTables:
        return ArchiveTables(
            readers={
                CsvExportKind.BOOKINGS: BookingRows(
                    self.booking_repo,
                    self.resource_repo,
                    self.knowledge_item_repo,
                    self.contact_repo,
                ),
                CsvExportKind.LEADS: LeadRows(self.lead_repo, self.contact_repo),
                CsvExportKind.CONTACTS: ContactRows(
                    self.contact_repo, self.phone_number_parser
                ),
                CsvExportKind.CONVERSATIONS: ConversationRows(
                    self.conversation_repo, self.contact_repo, self.message_repo
                ),
                CsvExportKind.AUDIT_LOG: AuditRows(self.audit_log_repo),
            }
        )
