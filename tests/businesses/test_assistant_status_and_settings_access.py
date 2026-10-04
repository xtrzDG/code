"""Pausing and resuming the assistant, and who may change the settings."""

import pytest

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import (
    BusinessQuery,
    BusinessSettingsChanges,
    InviteStaffCommand,
    InviteStaffRequest,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import EmailAddress
from tests.businesses.business_settings_steps import georgian_restaurant, update
from tests.users.accounts_phones import GERMANY_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed


def test_owner_may_only_pause_and_resume_a_live_assistant() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)

    with pytest.raises(ConflictError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(status=BusinessStatus.LIVE),
        )
    with pytest.raises(ConflictError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(status=BusinessStatus.PAUSED),
        )

    unchanged = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(status=BusinessStatus.ONBOARDING),
    )
    assert unchanged.status is BusinessStatus.ONBOARDING

    published = testbed.business_repo.get(business.id)
    assert published is not None
    published.status = BusinessStatus.LIVE
    testbed.business_repo.save(published)

    paused = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(status=BusinessStatus.PAUSED),
    )
    resumed = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(status=BusinessStatus.LIVE),
    )
    assert paused.status is BusinessStatus.PAUSED
    assert resumed.status is BusinessStatus.LIVE
    # Pausing switches the voice agent off; resuming re-activates the
    # published version (launch conditions and a new voice agent).
    assert testbed.voice_agent_removals.business_ids == [business.id]
    assert testbed.assistant_resumptions.business_ids == [business.id]

    with pytest.raises(ConflictError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(status=BusinessStatus.TESTING),
        )


def test_staff_and_strangers_cannot_change_settings() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)
    stranger = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=owner_id,
            business_id=business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(GERMANY_MOBILE)
            ),
        )
    )
    changes = BusinessSettingsChanges(name=BusinessName("Hijacked"))

    with pytest.raises(AccessDeniedError):
        update(testbed, staff.user.id, business.id, changes)
    with pytest.raises(NotFoundError):
        update(testbed, stranger.user.id, business.id, changes)
    with pytest.raises(NotFoundError):
        update(testbed, owner_id, BusinessId(), changes)

    staff_view = testbed.get_business.run(
        BusinessQuery(user_id=staff.user.id, business_id=business.id)
    )
    assert staff_view.name == "Sakhli"


def test_platform_admin_can_help_and_is_audited() -> None:
    testbed = build_accounts_testbed({"PLATFORM_ADMIN_EMAILS": "ops@example.com"})
    owner_id, business = georgian_restaurant(testbed)
    admin = UserDocument(
        login_method=LoginMethod.EMAIL,
        email=EmailAddress("ops@example.com"),
        locale=LanguageTag("ru"),
        is_platform_admin=True,
    )
    testbed.user_repo.save(admin)

    updated = update(
        testbed,
        admin.id,
        business.id,
        BusinessSettingsChanges(city=CityName("Kutaisi")),
    )

    assert updated.city == "Kutaisi"
    assert updated.viewer_role is None
    assert [
        entry.action for entry in testbed.audit_log_repo.list_by_business(business.id)
    ] == [AuditAction.ADMIN_ACCESS]
    assert owner_id != admin.id
