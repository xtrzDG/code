"""Journals, jobs and collection lookups behave the same in memory and on Postgres.

Every test runs twice through the `collections` fixture: once with the
in-memory collections, once with Postgres tables (skipped without Postgres).
"""

import pytest
from typed_time_provider import Microseconds

from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.booking_repositories import BookingRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import LlmTurnRepository
from app.repositories.job_repositories import QueuedJobRepository
from app.repositories.knowledge_repositories import KnowledgeItemRepository
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import LlmTurnDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.users.prefixed_id import UserId
from tests.storage.builders import (
    COUNTRY_SAMPLES,
    build_business,
    build_knowledge_item,
    build_llm_turn,
)
from tests.storage.conftest import CollectionFactory


def test_knowledge_bookings_and_usage(collections: CollectionFactory) -> None:
    knowledge_repo = KnowledgeItemRepository(
        collections(KnowledgeItemDocument, "knowledge_items")
    )
    booking_repo = BookingRepository(collections(BookingDocument, "bookings"))
    usage_repo = UsageEventRepository(collections(UsageEventDocument, "usage_events"))
    business_id = BusinessId()
    items = [build_knowledge_item(sample, business_id) for sample in COUNTRY_SAMPLES]
    for item in items:
        knowledge_repo.save(item)
    resource_id, contact_id = ResourceId(), ContactId()
    bookings = [
        BookingDocument(
            business_id=business_id,
            resource_id=resource_id,
            contact_id=contact_id,
            starts_at=BookingStartsAtUnixSeconds(starts_at),
            ends_at=BookingEndsAtUnixSeconds(starts_at + 5400),
            party_size=PartySize(4),
            source_channel=ChannelKind.WEB_CHAT,
        )
        for starts_at in (1_790_010_000, 1_790_000_000, 1_790_020_000)
    ]
    for booking in bookings:
        booking_repo.save(booking)
    for occurred_at, quantity in ((10, 60), (20, 1200), (30, 5)):
        usage_repo.append(
            UsageEventDocument(
                business_id=business_id,
                kind=UsageKind.VOICE_SECONDS,
                quantity=UsageQuantity(quantity),
                occurred_at=Microseconds(occurred_at),
            )
        )

    assert knowledge_repo.list_by_business(business_id) == items
    knowledge_repo.delete(business_id, items[0].id)
    assert knowledge_repo.get(business_id, items[0].id) is None
    assert knowledge_repo.get(BusinessId(), items[1].id) is None
    assert [
        booking.starts_at for booking in booking_repo.list_by_business(business_id)
    ] == [
        1_790_000_000,
        1_790_010_000,
        1_790_020_000,
    ]
    assert [
        event.quantity
        for event in usage_repo.list_by_business_between(
            business_id, Microseconds(15), Microseconds(40)
        )
    ] == [1200, 5]


def test_append_only_journals(collections: CollectionFactory) -> None:
    llm_turn_repo = LlmTurnRepository(collections(LlmTurnDocument, "llm_turns"))
    audit_log_repo = AuditLogRepository(
        collections(AuditLogEntryDocument, "audit_log_entries")
    )
    conversation_id, other_conversation_id = ConversationId(), ConversationId()
    turns = [
        build_llm_turn(conversation_id, sequence_number, text)
        for sequence_number, text in ((1, "second"), (0, "first"), (2, "third"))
    ]
    for turn in turns:
        llm_turn_repo.append(turn)
    llm_turn_repo.append(build_llm_turn(other_conversation_id, 0, "other"))
    entry = AuditLogEntryDocument(
        business_id=BusinessId(),
        action=AuditAction.EXPORT,
        entity=AuditEntityName("contact"),
    )
    audit_log_repo.append(entry)

    with pytest.raises(ConflictError):
        llm_turn_repo.append(turns[0])
    with pytest.raises(ConflictError):
        audit_log_repo.append(entry)
    assert [
        turn.sequence_number
        for turn in llm_turn_repo.list_by_conversation(conversation_id)
    ] == [0, 1, 2]
    llm_turn_repo.delete_by_conversation(conversation_id)
    assert llm_turn_repo.list_by_conversation(conversation_id) == []
    assert len(llm_turn_repo.list_by_conversation(other_conversation_id)) == 1
    assert entry.business_id is not None
    assert audit_log_repo.list_by_business(entry.business_id) == [entry]


def test_due_jobs_come_oldest_first(collections: CollectionFactory) -> None:
    job_repo = QueuedJobRepository(collections(QueuedJobDocument, "queued_jobs"))
    jobs = [
        QueuedJobDocument(
            name=JobName("send_booking_reminders"),
            payload=JobPayloadJson('{"language": "ka", "text": "შეხსენება"}'),
            business_id=BusinessId() if index % 2 == 0 else None,
            run_at=Microseconds(run_at),
            status=status,
        )
        for index, (run_at, status) in enumerate(
            (
                (300, QueuedJobStatus.PENDING),
                (100, QueuedJobStatus.PENDING),
                (200, QueuedJobStatus.DONE),
                (900, QueuedJobStatus.PENDING),
            )
        )
    ]
    for job in jobs:
        job_repo.save(job)

    due_jobs = job_repo.list_due(Microseconds(500))

    assert [job.run_at for job in due_jobs] == [100, 300]
    assert job_repo.get(jobs[3].id) == jobs[3]


def test_collections_return_fresh_copies_in_first_write_order(
    collections: CollectionFactory,
) -> None:
    businesses = collections(BusinessDocument, "businesses")
    stored = [build_business(sample, UserId()) for sample in COUNTRY_SAMPLES]
    for business in stored:
        businesses.upsert(str(business.id), business)
    businesses.upsert(str(stored[0].id), stored[0])

    loaded = businesses.list_all()
    loaded[1].members.clear()

    assert [business.id for business in loaded] == [business.id for business in stored]
    reloaded = businesses.get(str(stored[1].id))
    assert reloaded is not None
    assert len(reloaded.members) == 1


def test_field_lookups_find_documents_by_a_top_level_value(
    collections: CollectionFactory,
) -> None:
    contacts = collections(ContactDocument, "contacts")
    business_id = BusinessId()
    first = ContactDocument(
        business_id=business_id, phone_number=E164PhoneNumber("+995555123456")
    )
    second = ContactDocument(
        business_id=business_id, phone_number=E164PhoneNumber("+995555000000")
    )
    third = ContactDocument(
        business_id=BusinessId(), phone_number=E164PhoneNumber("+995555123456")
    )
    for contact in (first, second, third):
        contacts.upsert(str(contact.id), contact)

    found = contacts.list_by_field("phone_number", "+995555123456")

    assert [contact.id for contact in found] == [first.id, third.id]
    assert contacts.list_by_field("phone_number", "+1") == []
    assert contacts.list_by_field("no_such_field", "+995555123456") == []
