from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.booleans import IsDpaAccepted
from app.schemas.typings.compliance.constrained_integers import (
    DeletedRecordingCount,
    ErasedRecordCount,
    PurgedCallCount,
    ScannedBusinessCount,
)
from app.schemas.typings.compliance.constrained_strings import (
    DpaDocumentUrl,
    DpaDocumentVersion,
)
from app.schemas.typings.compliance.prefixed_id import (
    AuditLogEntryId,
    DpaAcceptanceId,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
    LegalDocumentMarkdown,
    LegalDocumentTitle,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class AcceptDpaCommand(ImmutableDTO):
    """Owner accepts the current data processing agreement for a business."""

    user_id: UserId
    business_id: BusinessId
    client_ip_address: ClientIpAddress | None = None


class DpaAcceptanceView(ImmutableDTO):
    """Who accepted which version of the agreement, and when."""

    id: DpaAcceptanceId
    document_version: DpaDocumentVersion
    accepted_by: UserId
    accepted_at: Microseconds


class DpaStatusView(ImmutableDTO):
    """
    Whether the business accepted the agreement version now in force.

    `document_url` is the API path of that version's text (None when the
    repository has no text for it; then it cannot be accepted).
    """

    business_id: BusinessId
    current_document_version: DpaDocumentVersion
    is_current_version_accepted: IsDpaAccepted
    latest_acceptance: DpaAcceptanceView | None = None
    document_url: DpaDocumentUrl | None = None


class DpaDocumentQuery(ImmutableDTO):
    """Anyone reads one version of the agreement, in a language if it exists."""

    version: DpaDocumentVersion
    language: LanguageTag | None = None


class DpaDocumentView(ImmutableDTO):
    """
    The text of one agreement version.

    `language` is the language served: the requested one, else its base
    language, else English. `available_languages` lists every translation.
    """

    version: DpaDocumentVersion
    language: LanguageTag
    available_languages: list[LanguageTag]
    title: LegalDocumentTitle
    text: LegalDocumentMarkdown


class AuditLogQuery(ImmutableDTO):
    """
    Owner reads the audit log of a business, newest first, one page at a
    time. Every filter is optional: the operation, the entity type, who did
    it, and the period `since` (inclusive) to `until` (exclusive) in UTC
    microseconds.
    """

    user_id: UserId
    business_id: BusinessId
    page: PageRequest = PageRequest()
    action: AuditAction | None = None
    entity: AuditEntityName | None = None
    actor_id: UserId | None = None
    since: Microseconds | None = None
    until: Microseconds | None = None


class AuditLogEntryView(ImmutableDTO):
    """One operation on personal data."""

    id: AuditLogEntryId
    action: AuditAction
    entity: AuditEntityName
    entity_id: AuditEntityReference | None = None
    actor_id: UserId | None = None
    ip_address: ClientIpAddress | None = None
    occurred_at: Microseconds


class AuditLogPage(ImmutableDTO):
    """
    One page of the audit log; `next_cursor` is None on the last page.

    `entities` and `actor_ids` list every entity type and every person in
    the whole log of the business (not only this page), for the filters.
    """

    items: list[AuditLogEntryView]
    next_cursor: PageCursor | None = None
    entities: list[AuditEntityName] = Field(default_factory=list[AuditEntityName])
    actor_ids: list[UserId] = Field(default_factory=list[UserId])


class ContactDataCommand(ImmutableDTO):
    """Owner exports or erases everything stored about one visitor."""

    user_id: UserId
    business_id: BusinessId
    contact_id: ContactId
    client_ip_address: ClientIpAddress | None = None


class ContactRecordsQuery(ImmutableDTO):
    """Collect the records of one visitor inside one business."""

    business_id: BusinessId
    contact_id: ContactId


class ContactRecords(ImmutableDTO):
    """
    Every stored record that describes one visitor of one business.

    Calls belong to the visitor through one of their conversations or their
    phone number. Raw language-model turns repeat the messages and are not
    listed.
    """

    contact: ContactDocument
    conversations: list[ConversationDocument] = Field(
        default_factory=list[ConversationDocument]
    )
    messages: list[MessageDocument] = Field(default_factory=list[MessageDocument])
    calls: list[CallDocument] = Field(default_factory=list[CallDocument])
    bookings: list[BookingDocument] = Field(default_factory=list[BookingDocument])
    leads: list[LeadDocument] = Field(default_factory=list[LeadDocument])
    handoffs: list[HandoffDocument] = Field(default_factory=list[HandoffDocument])


class ContactDataExport(ImmutableDTO):
    """Machine-readable copy of a visitor's personal data (right of access)."""

    business_id: BusinessId
    exported_at: Microseconds
    records: ContactRecords


class ContactErasureResult(ImmutableDTO):
    """
    What a visitor's erasure removed.

    Messages, model transcripts, call transcripts and recordings are deleted;
    conversations, bookings, leads and handoffs stay as anonymous business
    records.
    """

    business_id: BusinessId
    contact_id: ContactId
    deleted_messages: ErasedRecordCount
    deleted_llm_turns: ErasedRecordCount
    erased_calls: ErasedRecordCount
    deleted_recordings: DeletedRecordingCount
    anonymized_conversations: ErasedRecordCount
    anonymized_bookings: ErasedRecordCount
    anonymized_leads: ErasedRecordCount
    anonymized_handoffs: ErasedRecordCount


class PurgeExpiredRecordingsCommand(ImmutableDTO):
    """Run the retention purge for one business, or for all when None."""

    business_id: BusinessId | None = None


class RecordingPurgeResult(ImmutableDTO):
    """Counts of one retention purge run."""

    scanned_businesses: ScannedBusinessCount
    purged_calls: PurgedCallCount
    deleted_recordings: DeletedRecordingCount
