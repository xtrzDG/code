"""Reading a business's audit log: newest first, filters, admin access."""

import pytest

from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.compliance import AcceptDpaCommand, AuditLogQuery
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.constrained_strings import EmailAddress
from tests.compliance.business_with_staff import business_with_staff
from tests.foundation.support_access_builders import as_request, open_support_session
from tests.users.accounts_phones import ISRAEL_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed


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
    ).items
    first_page = testbed.list_audit_log.run(
        AuditLogQuery(
            user_id=owner_id,
            business_id=business.id,
            page=PageRequest(size=PageSize(3)),
        )
    )
    second_page = testbed.list_audit_log.run(
        AuditLogQuery(
            user_id=owner_id,
            business_id=business.id,
            page=PageRequest(size=PageSize(3), cursor=first_page.next_cursor),
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
    assert first_page.items == entries[:3]
    assert first_page.next_cursor is not None
    assert second_page.items == entries[3:]
    assert second_page.next_cursor is None
    with pytest.raises(AccessDeniedError):
        testbed.list_audit_log.run(
            AuditLogQuery(user_id=staff_id, business_id=business.id)
        )


def test_audit_log_filters_run_before_paging_and_name_the_filter_values() -> None:
    testbed = build_accounts_testbed()
    owner_id, staff_id, business = business_with_staff(testbed)
    started = testbed.clock.now_microseconds()
    testbed.clock.advance(60)
    testbed.accept_dpa.run(AcceptDpaCommand(user_id=owner_id, business_id=business.id))
    accepted_at = testbed.clock.now_microseconds()
    testbed.clock.advance(60)
    testbed.accept_dpa.run(AcceptDpaCommand(user_id=owner_id, business_id=business.id))

    def query(**filters: object) -> list[str]:
        page = testbed.list_audit_log.run(
            AuditLogQuery.model_validate(
                {"user_id": owner_id, "business_id": business.id, **filters}
            )
        )
        return [str(entry.entity) for entry in page.items]

    everything = testbed.list_audit_log.run(
        AuditLogQuery(user_id=owner_id, business_id=business.id)
    )

    assert query(
        action=AuditAction.CREATE, entity=AuditEntityName("dpa_acceptance")
    ) == [
        "dpa_acceptance",
        "dpa_acceptance",
    ]
    assert query(entity=AuditEntityName("business_member")) == ["business_member"]
    assert query(actor_id=staff_id) == []
    assert query(since=accepted_at) == ["dpa_acceptance", "dpa_acceptance"]
    assert query(since=accepted_at, until=accepted_at + 1) == ["dpa_acceptance"]
    assert query(until=started + 1) == ["business_member"]
    assert everything.entities == ["business_member", "dpa_acceptance"]
    assert everything.actor_ids == [owner_id]


def test_platform_support_reads_the_audit_log_only_during_an_open_look() -> None:
    testbed = build_accounts_testbed({"PLATFORM_ADMIN_EMAILS": "ops@example.com"})
    _, _, business = business_with_staff(testbed)
    admin = UserDocument(
        login_method=LoginMethod.EMAIL,
        email=EmailAddress("ops@example.com"),
        locale=LanguageTag("en"),
        is_platform_admin=True,
    )
    testbed.user_repo.save(admin)

    def read() -> object:
        return testbed.list_audit_log.run(
            AuditLogQuery(user_id=admin.id, business_id=business.id)
        )

    with pytest.raises(AccessDeniedError, match="reason first"):
        as_request(testbed.session_assurance, admin.id, read, BusinessAccessMode.READ)
    open_support_session(
        testbed.grant_repo, business.id, admin.id, int(testbed.clock.now_microseconds())
    )

    page = as_request(
        testbed.session_assurance, admin.id, read, BusinessAccessMode.READ
    )
    assert getattr(page, "items", None) is not None
