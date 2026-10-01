"""
The foundation repositories behave the same on in-memory and on Postgres.

Every test runs twice through the `collections` fixture: once with the
in-memory collections, once with Postgres tables (skipped without Postgres).
"""

import pytest
from typed_time_provider import Microseconds

from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.booking_repositories import BookingRepository
from app.repositories.business_repositories import (
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    LlmTurnRepository,
)
from app.repositories.job_repositories import QueuedJobRepository
from app.repositories.knowledge_repositories import KnowledgeItemRepository
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserRepository,
    UserSessionRepository,
)
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import LlmTurnDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessTokenHash, OtpCodeHash
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from tests.storage.builders import (
    COUNTRY_SAMPLES,
    build_business,
    build_contact,
    build_email_user,
    build_knowledge_item,
    build_llm_turn,
    build_owner,
)
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import FIXED_NANOSECONDS, build_fixed_wall_clock

GEORGIA, ISRAEL, EMIRATES, JAPAN, BRAZIL, KAZAKHSTAN = COUNTRY_SAMPLES
NOW_MICROSECONDS: int = FIXED_NANOSECONDS // 1_000


def test_business_access_for_owner_staff_stranger_and_admin(
    collections: CollectionFactory,
) -> None:
    business_repo = BusinessRepository(collections(BusinessDocument, "businesses"))
    user_repo = UserRepository(collections(UserDocument, "users"))
    audit_log_repo = AuditLogRepository(
        collections(AuditLogEntryDocument, "audit_log_entries")
    )
    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                AuthorizeBusinessAccessUseCase(
                    business_repo=business_repo,
                    user_repo=user_repo,
                    audit_log_repo=audit_log_repo,
                    wall_clock=build_fixed_wall_clock(),
                )
            )
        )
    )
    owner, staff = build_owner(ISRAEL), build_owner(EMIRATES)
    business = build_business(ISRAEL, owner.id)
    business.members.append(
        BusinessMember(user_id=staff.id, role=BusinessMemberRole.STAFF)
    )
    admin = build_email_user("admin@example.com", "ru")
    admin.is_platform_admin = True
    for user in (owner, staff, admin):
        user_repo.save(user)
    business_repo.save(business)

    owner_request = BusinessAccessRequest(
        user_id=owner.id,
        business_id=business.id,
        required_role=BusinessMemberRole.OWNER,
    )
    assert operator.operate(owner_request).id == business.id
    assert (
        operator.operate(
            BusinessAccessRequest(user_id=staff.id, business_id=business.id)
        ).name
        == ISRAEL.business_name
    )
    with pytest.raises(AccessDeniedError):
        operator.operate(
            BusinessAccessRequest(
                user_id=staff.id,
                business_id=business.id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
    with pytest.raises(NotFoundError):
        operator.operate(
            BusinessAccessRequest(user_id=UserId(), business_id=business.id)
        )
    assert (
        operator.operate(
            BusinessAccessRequest(user_id=admin.id, business_id=business.id)
        ).id
        == business.id
    )
    entries = audit_log_repo.list_by_business(business.id)
    assert [entry.action for entry in entries] == [AuditAction.ADMIN_ACCESS]
    assert entries[0].actor_id == admin.id
    assert [found.id for found in business_repo.list_by_member(staff.id)] == [
        business.id
    ]


def test_users_sessions_and_codes(collections: CollectionFactory) -> None:
    user_repo = UserRepository(collections(UserDocument, "users"))
    session_repo = UserSessionRepository(
        collections(UserSessionDocument, "user_sessions")
    )
    challenge_repo = OtpChallengeRepository(
        collections(OtpChallengeDocument, "otp_challenges")
    )
    users = [build_owner(sample) for sample in COUNTRY_SAMPLES]
    email_user = build_email_user("noa@example.co.il", "he")
    for user in [*users, email_user]:
        user_repo.save(user)
    session = UserSessionDocument(
        user_id=email_user.id,
        token_hash=AccessTokenHash("a" * 64),
        expires_at=Microseconds(NOW_MICROSECONDS + 60_000_000),
    )
    session_repo.save(session)
    old_challenge, new_challenge = (
        OtpChallengeDocument(
            login_method=LoginMethod.PHONE,
            phone_number=E164PhoneNumber(sample.phone_number),
            delivery_channel=OtpDeliveryChannel.WHATSAPP,
            locale=LanguageTag(sample.language),
            code_hash=OtpCodeHash(f"hash-{sample.country_code}"),
            expires_at=Microseconds(NOW_MICROSECONDS + 600_000_000),
            created_at=Microseconds(created_at),
            updated_at=Microseconds(created_at),
        )
        for sample, created_at in (
            (JAPAN, NOW_MICROSECONDS - 3_600_000_000),
            (KAZAKHSTAN, NOW_MICROSECONDS),
        )
    )
    challenge_repo.save(old_challenge)
    challenge_repo.save(new_challenge)

    for sample, user in zip(COUNTRY_SAMPLES, users, strict=True):
        assert user_repo.find_by_phone_number(E164PhoneNumber(sample.phone_number)) == (
            user
        )
    assert email_user.email is not None
    assert user_repo.find_by_email(email_user.email) == email_user
    assert user_repo.find_by_phone_number(E164PhoneNumber("+14155550100")) is None
    assert session_repo.find_by_token_hash(AccessTokenHash("a" * 64)) == session
    session_repo.delete(session.id)
    assert session_repo.find_by_token_hash(AccessTokenHash("a" * 64)) is None
    assert [
        challenge.id
        for challenge in challenge_repo.list_created_since(
            Microseconds(NOW_MICROSECONDS - 60_000_000)
        )
    ] == [new_challenge.id]


def test_contacts_are_found_only_inside_their_business(
    collections: CollectionFactory,
) -> None:
    contact_repo = ContactRepository(collections(ContactDocument, "contacts"))
    first_business_id, second_business_id = BusinessId(), BusinessId()
    contacts = [
        build_contact(sample, first_business_id) for sample in (GEORGIA, ISRAEL)
    ]
    for contact in contacts:
        contact_repo.save(contact)
    foreign_contact = build_contact(BRAZIL, second_business_id)
    contact_repo.save(foreign_contact)

    assert (
        contact_repo.find_by_phone_number(
            first_business_id, E164PhoneNumber(ISRAEL.phone_number)
        )
        == (contacts[1])
    )
    assert (
        contact_repo.find_by_phone_number(
            second_business_id, E164PhoneNumber(ISRAEL.phone_number)
        )
        is None
    )
    assert contact_repo.find_by_channel_identity(
        second_business_id,
        ChannelKind.WHATSAPP,
        ChannelUserId(BRAZIL.phone_number.removeprefix("+")),
    ) == (foreign_contact)
    assert {
        contact.id for contact in contact_repo.list_by_business(first_business_id)
    } == {contact.id for contact in contacts}
    contact_repo.delete(second_business_id, contacts[0].id)
    assert contact_repo.get(first_business_id, contacts[0].id) == contacts[0]
    contact_repo.delete(first_business_id, contacts[0].id)
    assert contact_repo.get(first_business_id, contacts[0].id) is None


def test_channel_routing_finds_the_business_of_a_webhook(
    collections: CollectionFactory,
) -> None:
    channel_repo = ChannelRepository(collections(ChannelDocument, "channels"))
    channels = [
        ChannelDocument(
            business_id=BusinessId(),
            kind=kind,
            external_id=ChannelExternalId(external_id),
            status=ChannelStatus.CONNECTED,
        )
        for kind, external_id in (
            (ChannelKind.TELEGRAM, "bot:7001"),
            (ChannelKind.WHATSAPP, "+995322000000"),
            (ChannelKind.TELEGRAM, "bot:7002"),
        )
    ]
    for channel in channels:
        channel_repo.save(channel)

    found = channel_repo.find_by_external_id(
        ChannelKind.TELEGRAM, ChannelExternalId("bot:7002")
    )

    assert found == channels[2]
    assert (
        channel_repo.find_by_external_id(
            ChannelKind.WHATSAPP, ChannelExternalId("bot:7002")
        )
        is None
    )
    assert channel_repo.list_by_business(channels[0].business_id) == [channels[0]]


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
