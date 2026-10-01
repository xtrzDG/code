import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import (
    BusinessQuery,
    InviteStaffCommand,
    InviteStaffRequest,
)
from app.schemas.dto.compliance import AcceptDpaCommand, AuditLogQuery
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.compliance.constrained_integers import AuditLogPageSize
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.compliance.get_dpa_status_use_case import GetDpaStatusUseCase
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings
from tests.users.accounts_testbed import (
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    ISRAEL_MOBILE,
    AccountsTestbed,
    build_accounts_testbed,
)


def business_with_staff(
    testbed: AccountsTestbed,
) -> tuple[UserId, UserId, BusinessDocument]:
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=owner.user.id,
            business_id=business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(GERMANY_MOBILE)
            ),
        )
    )
    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)
    return owner.user.id, staff.user.id, business


def test_owner_accepts_the_current_agreement_version() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": "2026-11-15"})
    owner_id, staff_id, business = business_with_staff(testbed)

    before = testbed.get_dpa_status.run(
        BusinessQuery(user_id=staff_id, business_id=business.id)
    )
    accepted = testbed.accept_dpa.run(
        AcceptDpaCommand(
            user_id=owner_id,
            business_id=business.id,
            client_ip_address=ClientIpAddress("2001:db8::1"),
        )
    )
    after = testbed.get_dpa_status.run(
        BusinessQuery(user_id=staff_id, business_id=business.id)
    )

    assert before.is_current_version_accepted is False
    assert before.latest_acceptance is None
    assert before.current_document_version == "2026-11-15"
    assert accepted.is_current_version_accepted is True
    assert after == accepted
    assert after.latest_acceptance is not None
    assert after.latest_acceptance.accepted_by == owner_id
    assert after.latest_acceptance.document_version == "2026-11-15"
    assert after.latest_acceptance.accepted_at == testbed.clock.now_microseconds()
    stored = testbed.dpa_acceptance_repo.list_by_business(business.id)
    assert [acceptance.document_version for acceptance in stored] == ["2026-11-15"]
    dpa_entries = [
        entry
        for entry in testbed.audit_log_repo.list_by_business(business.id)
        if entry.entity == "dpa_acceptance"
    ]
    assert len(dpa_entries) == 1
    assert dpa_entries[0].action is AuditAction.CREATE
    assert dpa_entries[0].ip_address == "2001:db8::1"


def test_new_agreement_version_needs_a_new_acceptance() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": "2026-10-01"})
    owner_id, _, business = business_with_staff(testbed)
    testbed.accept_dpa.run(AcceptDpaCommand(user_id=owner_id, business_id=business.id))
    newer_settings = assemble_app_settings({"DPA_DOCUMENT_VERSION": "2027-01-01"})
    status_with_new_version = GetDpaStatusUseCase(
        authorize_business_access=testbed.authorize_business_access,
        dpa_acceptance_repo=testbed.dpa_acceptance_repo,
        app_settings=newer_settings,
    ).run(BusinessQuery(user_id=owner_id, business_id=business.id))

    assert status_with_new_version.current_document_version == "2027-01-01"
    assert status_with_new_version.is_current_version_accepted is False
    assert status_with_new_version.latest_acceptance is not None
    assert status_with_new_version.latest_acceptance.document_version == "2026-10-01"


def test_only_owners_accept_and_strangers_see_nothing() -> None:
    testbed = build_accounts_testbed()
    _, staff_id, business = business_with_staff(testbed)
    stranger = testbed.sign_in_with_phone(ISRAEL_MOBILE)

    with pytest.raises(AccessDeniedError):
        testbed.accept_dpa.run(
            AcceptDpaCommand(user_id=staff_id, business_id=business.id)
        )
    with pytest.raises(NotFoundError):
        testbed.get_dpa_status.run(
            BusinessQuery(user_id=stranger.user.id, business_id=business.id)
        )
    assert testbed.dpa_acceptance_repo.list_by_business(business.id) == []


def test_owner_reads_the_newest_audit_entries_of_their_business_only() -> None:
    testbed = build_accounts_testbed()
    owner_id, staff_id, business = business_with_staff(testbed)
    other_owner = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    other_business = testbed.create_restaurant(other_owner.user.id)
    testbed.accept_dpa.run(
        AcceptDpaCommand(user_id=other_owner.user.id, business_id=other_business.id)
    )
    for _ in range(3):
        testbed.clock.advance(1)
        testbed.accept_dpa.run(
            AcceptDpaCommand(user_id=owner_id, business_id=business.id)
        )

    entries = testbed.list_audit_log.run(
        AuditLogQuery(user_id=owner_id, business_id=business.id)
    )
    limited = testbed.list_audit_log.run(
        AuditLogQuery(
            user_id=owner_id,
            business_id=business.id,
            limit=AuditLogPageSize(2),
        )
    )

    assert [entry.entity for entry in entries] == [
        "dpa_acceptance",
        "dpa_acceptance",
        "dpa_acceptance",
        "business_member",
    ]
    assert [entry.occurred_at for entry in entries] == sorted(
        (entry.occurred_at for entry in entries),
        reverse=True,
    )
    assert entries[-1].action is AuditAction.CREATE
    assert entries[-1].entity_id == str(staff_id)
    assert limited == entries[:2]
    with pytest.raises(AccessDeniedError):
        testbed.list_audit_log.run(
            AuditLogQuery(user_id=staff_id, business_id=business.id)
        )


def test_platform_admin_reading_the_audit_log_is_itself_audited() -> None:
    testbed = build_accounts_testbed()
    _, _, business = business_with_staff(testbed)
    admin = UserDocument(
        login_method=LoginMethod.EMAIL,
        locale=LanguageTag("en"),
        is_platform_admin=True,
    )
    testbed.user_repo.save(admin)

    entries = testbed.list_audit_log.run(
        AuditLogQuery(user_id=admin.id, business_id=business.id)
    )

    assert entries[0].action is AuditAction.ADMIN_ACCESS
    assert entries[0].actor_id == admin.id
