"""
The archive of a full business export: a ZIP with a JSON file per
collection of the business's data and the cabinet's tables as CSV (the
same rows as their downloads), with a README. Erased customers are left
out; secrets never leave (channel credentials are not exported at all,
review link tokens are dropped).
"""

import io
import json
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
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
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.privacy.csv_exports import CsvRow
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.privacy.constrained_integers import ExportedRecordCount
from app.use_cases.exports.archive_paging import read_all
from app.use_cases.exports.business_rows import booking_row, is_erased, lead_row
from app.use_cases.exports.growth_archive import growth_documents
from app.use_cases.exports.people_rows import (
    audit_row,
    contact_row,
    conversation_rows,
    is_test_only,
)
from app.utilities.privacy.csv_cells import moment_cell
from app.utilities.privacy.csv_columns import CSV_COLUMNS
from app.utilities.privacy.csv_writing import csv_text
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import load_time_zone

README: str = """Full export of {business}, made {made_at} ({timezone}).

JSON: one file per kind of record, as the platform keeps them (times are
UTC microseconds since 1970). CSV: the cabinet's tables, as their
downloads (local times, UTF-8). Customers who asked to be erased are not
in it; channel credentials and review link tokens never leave the
platform.
"""


@dataclass(frozen=True)
class BuiltArchive:
    content: bytes
    record_count: ExportedRecordCount


@dataclass(frozen=True)
class BusinessArchiveBuilder:
    contact_repo: ContactRepoContract
    conversation_repo: ConversationRepoContract
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
    waitlist_entry_repo: WaitlistEntryRepoContract | None = None
    campaign_message_repo: CampaignMessageRepoContract | None = None

    def build(
        self, business: BusinessDocument, language: LanguageTag, now: Microseconds
    ) -> BuiltArchive:
        business_id = business.id
        zone: ZoneInfo = load_time_zone(business.timezone)
        all_contacts = self.contact_repo.list_by_business(business_id)
        contacts: dict[ContactId, ContactDocument] = {
            contact.id: contact for contact in all_contacts
        }
        customers = [
            contact
            for contact in all_contacts
            if not is_erased(contact) and not is_test_only(contact)
        ]
        conversations = [
            conversation
            for conversation in self.conversation_repo.list_by_business(business_id)
            if not is_erased(contacts.get(conversation.contact_id))
        ]
        messages = self.message_repo.list_by_business(business_id)
        bookings = self.booking_repo.list_by_business(business_id)
        leads = self.lead_repo.list_by_business(business_id)
        resources = self.resource_repo.list_by_business(business_id)
        services = self.knowledge_item_repo.list_by_business(business_id)
        audit_log = self.audit_log_repo.list_by_business(business_id)
        missed_calls: list[MissedCallDocument] = read_all(
            lambda window: self.missed_call_repo.page_by_business(business_id, window),
            lambda call: int(call.created_at),
        )
        feedback_requests: list[FeedbackRequestDocument] = read_all(
            lambda window: self.feedback_request_repo.page_by_business(
                business_id, window
            ),
            lambda request: int(request.created_at),
        )
        collections: dict[str, Sequence[BaseDocument]] = {
            "business": [business],
            "contacts": customers,
            "conversations": conversations,
            "messages": messages,
            "calls": self.call_repo.list_by_business(business_id),
            "bookings": bookings,
            "leads": leads,
            "handoffs": self.handoff_repo.list_by_business(business_id),
            "resources": resources,
            "knowledge_items": services,
            "missed_calls": missed_calls,
            "feedback_requests": feedback_requests,
            **growth_documents(
                business_id, self.waitlist_entry_repo, self.campaign_message_repo
            ),
            "audit_log": audit_log,
        }
        by_conversation: dict[ConversationId, list[MessageDocument]] = {}
        for message in messages:
            by_conversation.setdefault(message.conversation_id, []).append(message)

        resource_by_id = {resource.id: resource for resource in resources}
        service_by_id = {service.id: service for service in services}
        tables: dict[CsvExportKind, list[CsvRow]] = {
            CsvExportKind.BOOKINGS: [
                booking_row(
                    build_booking_view(
                        booking,
                        business.timezone,
                        zone,
                        resource_by_id.get(booking.resource_id),
                        contacts.get(booking.contact_id),
                        None
                        if booking.service_item_id is None
                        else service_by_id.get(booking.service_item_id),
                    ),
                    zone,
                )
                for booking in bookings
                if not is_erased(contacts.get(booking.contact_id))
            ],
            CsvExportKind.LEADS: [
                lead_row(lead, contacts.get(lead.contact_id), zone)
                for lead in leads
                if not is_erased(contacts.get(lead.contact_id))
            ],
            CsvExportKind.CONTACTS: [contact_row(item, zone) for item in customers],
            CsvExportKind.CONVERSATIONS: [
                row
                for conversation in conversations
                for row in conversation_rows(
                    conversation,
                    contacts.get(conversation.contact_id),
                    by_conversation.get(conversation.id, []),
                    zone,
                )
            ],
            CsvExportKind.AUDIT_LOG: [audit_row(entry, zone) for entry in audit_log],
        }
        return BuiltArchive(
            content=self._zip(business, language, now, zone, collections, tables),
            record_count=ExportedRecordCount(
                sum(len(documents) for documents in collections.values())
            ),
        )

    def _zip(
        self,
        business: BusinessDocument,
        language: LanguageTag,
        now: Microseconds,
        zone: ZoneInfo,
        collections: dict[str, Sequence[BaseDocument]],
        tables: dict[CsvExportKind, list[CsvRow]],
    ) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "README.txt",
                README.format(
                    business=business.name,
                    made_at=str(moment_cell(now, zone)),
                    timezone=business.timezone,
                ),
            )
            for name, documents in collections.items():
                archive.writestr(f"{name}.json", documents_json(documents))
            for kind, rows in tables.items():
                header = [
                    str(self.text_resolver.resolve(title, language))
                    for title in CSV_COLUMNS[kind]
                ]
                cells = ([str(cell) for cell in row.cells] for row in rows)
                archive.writestr(f"csv/{kind.value}.csv", csv_text(header, cells))
        return buffer.getvalue()


# Fields that are keys to something, not data of the business.
SECRET_FIELDS: frozenset[str] = frozenset({"review_token"})


def documents_json(documents: Sequence[BaseDocument]) -> str:
    return json.dumps(
        [
            document.model_dump(mode="json", exclude=set(SECRET_FIELDS))
            for document in documents
        ],
        ensure_ascii=False,
        indent=2,
    )
