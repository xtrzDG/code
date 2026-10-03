"""The manager contacts in the business settings, validated per channel."""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.dto.businesses import BusinessSettingsChanges, ManagerContactInput
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.strings import (
    BusinessName,
    RawManagerContactAddress,
)
from app.schemas.typings.handoffs.strings import ManagerName
from tests.businesses.business_settings_steps import (
    contact,
    georgian_restaurant,
    update,
)
from tests.users.accounts_phones import GERMANY_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed


def test_manager_contacts_are_validated_per_channel() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)

    updated = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            manager_contacts=[
                contact(ManagerContactChannel.TELEGRAM, " 123456789 "),
                contact(ManagerContactChannel.TELEGRAM, "-1001234567890", "ru"),
                contact(ManagerContactChannel.WHATSAPP, "599 12 34 56"),
                contact(ManagerContactChannel.SMS, GERMANY_MOBILE, "de"),
                contact(ManagerContactChannel.EMAIL, " Manager@Example.COM ", "he"),
            ]
        ),
    )

    assert [
        (manager.channel, manager.address, manager.language)
        for manager in updated.manager_contacts
    ] == [
        (ManagerContactChannel.TELEGRAM, "123456789", "ka"),
        (ManagerContactChannel.TELEGRAM, "-1001234567890", "ru"),
        (ManagerContactChannel.WHATSAPP, "+995599123456", "ka"),
        (ManagerContactChannel.SMS, "+4915123456789", "de"),
        (ManagerContactChannel.EMAIL, "manager@example.com", "he"),
    ]
    audit_entries = testbed.audit_log_repo.list_by_business(business.id)
    assert [(entry.action, entry.entity) for entry in audit_entries] == [
        (AuditAction.UPDATE, "manager_contacts")
    ]
    assert audit_entries[0].actor_id == owner_id

    emptied = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(manager_contacts=[]),
    )
    assert emptied.manager_contacts == []


def test_national_numbers_of_manager_contacts_use_the_business_country() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    business = testbed.create_restaurant(owner.user.id, "Shuk")

    updated = update(
        testbed,
        owner.user.id,
        business.id,
        BusinessSettingsChanges(
            manager_contacts=[contact(ManagerContactChannel.WHATSAPP, "050-234-5678")]
        ),
    )

    assert updated.manager_contacts[0].address == "+972502345678"
    assert updated.manager_contacts[0].language == "he"


@pytest.mark.parametrize(
    ("manager_contact", "expected_error"),
    [
        (contact(ManagerContactChannel.TELEGRAM, "@manager"), ValidationFailedError),
        (contact(ManagerContactChannel.TELEGRAM, "12 34"), ValidationFailedError),
        (contact(ManagerContactChannel.WHATSAPP, "12"), InvalidPhoneNumberError),
        (contact(ManagerContactChannel.SMS, "not a phone"), InvalidPhoneNumberError),
        (contact(ManagerContactChannel.EMAIL, "manager@"), ValidationFailedError),
        (contact(ManagerContactChannel.EMAIL, "a@b.c", "xh"), UnsupportedLanguageError),
        (
            ManagerContactInput(
                name=ManagerName("  "),
                channel=ManagerContactChannel.TELEGRAM,
                address=RawManagerContactAddress("42"),
            ),
            ValidationFailedError,
        ),
    ],
)
def test_invalid_manager_contacts_change_nothing(
    manager_contact: ManagerContactInput,
    expected_error: type[Exception],
) -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)

    with pytest.raises(expected_error):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(
                name=BusinessName("Should not be saved"),
                manager_contacts=[manager_contact],
            ),
        )

    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.name == "Sakhli"
    assert stored.manager_contacts == []
    assert testbed.audit_log_repo.list_by_business(business.id) == []


def test_too_many_manager_contacts_are_refused() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)

    with pytest.raises(ValidationFailedError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(
                manager_contacts=[
                    contact(ManagerContactChannel.TELEGRAM, str(chat_id))
                    for chat_id in range(21)
                ]
            ),
        )
