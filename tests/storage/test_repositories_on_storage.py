"""The foundation repositories behave the same on in-memory and on Postgres.

Every test runs twice through the `collections` fixture: once with the
in-memory collections, once with Postgres tables (skipped without Postgres).
These cover access, accounts, contacts, channel routing and business saves.
"""

import pytest
from typed_time_provider import Microseconds

from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.business_repositories import BusinessRepository, ChannelRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import ContactRepository
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserRepository,
    UserSessionRepository,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessTokenHash, OtpCodeHash
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.access_support import ACCESS_SETTINGS, PLATFORM_ADMIN_EMAIL
from tests.foundation.support_access_builders import build_authorize_business_access
from tests.storage.builders import (
    COUNTRY_SAMPLES,
    build_business,
    build_contact,
    build_email_user,
    build_owner,
)
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import FIXED_NANOSECONDS, build_fixed_wall_clock

# Seeding and checking rows of several businesses runs platform-wide; the
# business scopes a test enters nest inside (tests/storage/conftest.py).
pytestmark = pytest.mark.usefixtures("platform_scope")

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
                build_authorize_business_access(
                    business_repo=business_repo,
                    user_repo=user_repo,
                    audit_log_repo=audit_log_repo,
                    wall_clock=build_fixed_wall_clock(),
                    session_assurance=SessionAssuranceContext(),
                    app_settings=ACCESS_SETTINGS,
                )
            )
        )
    )
    owner, staff = build_owner(ISRAEL), build_owner(EMIRATES)
    business = build_business(ISRAEL, owner.id)
    business.members.append(
        BusinessMember(user_id=staff.id, role=BusinessMemberRole.STAFF)
    )
    admin = build_email_user(PLATFORM_ADMIN_EMAIL, "ru")
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


def test_business_saves_raise_the_revision_and_stale_copies_are_refused(
    collections: CollectionFactory,
) -> None:
    business_repo = BusinessRepository(collections(BusinessDocument, "businesses"))
    business = build_business(GEORGIA, UserId())
    business_repo.save(business)
    first_tab = business_repo.get(business.id)
    second_tab = business_repo.get(business.id)
    assert first_tab is not None and second_tab is not None

    first_tab.name = BusinessName("First tab")
    is_first_saved = business_repo.save_if_unchanged(first_tab)
    second_tab.name = BusinessName("Second tab")
    is_second_saved = business_repo.save_if_unchanged(second_tab)

    assert (is_first_saved, is_second_saved) == (True, False)
    assert (first_tab.revision, second_tab.revision) == (2, 1)
    stored = business_repo.get(business.id)
    assert stored is not None
    assert (stored.name, stored.revision) == ("First tab", 2)
    # A plain save of a stale copy still never lowers the revision.
    business_repo.save(second_tab)
    assert second_tab.revision == 3
    assert business_repo.save_if_unchanged(first_tab) is False
    missing = build_business(ISRAEL, UserId())
    assert business_repo.save_if_unchanged(missing) is False
    assert business_repo.get(missing.id) is None
