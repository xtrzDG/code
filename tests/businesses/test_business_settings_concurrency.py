"""Settings saves that race other saves, status switches and invitations."""

import pytest

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import (
    BusinessQuery,
    BusinessSettingsChanges,
    InviteStaffCommand,
    InviteStaffRequest,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.constrained_integers import BusinessRevision
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from tests.businesses.business_settings_steps import (
    contact,
    georgian_restaurant,
    update,
)
from tests.users.accounts_phones import GERMANY_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


def test_settings_changed_since_they_were_opened_are_not_overwritten() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    opened = testbed.get_business.run(
        BusinessQuery(user_id=owner_id, business_id=business.id)
    )
    audit_entries_before = len(testbed.audit_log_collection.list_all())

    first = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            expected_revision=opened.revision, city=CityName("Batumi")
        ),
    )
    with pytest.raises(ConflictError, match="saved by someone else") as refusal:
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(
                expected_revision=opened.revision,
                name=BusinessName("Old tab"),
                manager_contacts=[contact(ManagerContactChannel.TELEGRAM, "70001")],
            ),
        )

    assert first.revision == BusinessRevision(int(opened.revision) + 1)
    [reason] = refusal.value.reasons
    assert reason.code == "stale_revision"
    assert reason.details == [str(int(first.revision))]
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert (stored.name, stored.city) == ("Sakhli", "Batumi")
    assert stored.manager_contacts == []
    assert stored.revision == first.revision
    # The refused contact change is not in the audit log either.
    assert len(testbed.audit_log_collection.list_all()) == audit_entries_before
    # From the current revision, or without one (scripts), the change applies.
    current = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            expected_revision=first.revision, name=BusinessName("New tab")
        ),
    )
    unchecked = update(
        testbed, owner_id, business.id, BusinessSettingsChanges(city=CityName("Gori"))
    )
    assert (current.name, unchecked.city) == ("New tab", "Gori")
    assert unchecked.revision == BusinessRevision(int(first.revision) + 2)


def test_a_save_between_reading_and_writing_is_not_overwritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    repo = testbed.business_repo
    save_if_unchanged = repo.save_if_unchanged

    def save_after_a_manager_linked_the_bot(document: BusinessDocument) -> bool:
        # Another request saves the business after this one read it.
        meanwhile = repo.get(business.id)
        assert meanwhile is not None
        meanwhile.city = CityName("Kutaisi")
        repo.save(meanwhile)
        return save_if_unchanged(document)

    monkeypatch.setattr(repo, "save_if_unchanged", save_after_a_manager_linked_the_bot)

    with pytest.raises(ConflictError, match="saved by someone else"):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(name=BusinessName("Lost update")),
        )

    stored = repo.get(business.id)
    assert stored is not None
    assert (stored.name, stored.city) == ("Sakhli", "Kutaisi")


def make_live(testbed: AccountsTestbed, business_id: BusinessId) -> None:
    live = testbed.business_repo.get(business_id)
    assert live is not None
    live.status = BusinessStatus.LIVE
    testbed.business_repo.save(live)


def test_a_pause_refused_as_stale_keeps_the_voice_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    make_live(testbed, business.id)
    repo = testbed.business_repo
    save_if_unchanged = repo.save_if_unchanged

    def save_after_a_billing_job(document: BusinessDocument) -> bool:
        meanwhile = repo.get(business.id)
        assert meanwhile is not None
        meanwhile.city = CityName("Kutaisi")
        repo.save(meanwhile)
        return save_if_unchanged(document)

    monkeypatch.setattr(repo, "save_if_unchanged", save_after_a_billing_job)

    with pytest.raises(ConflictError, match="saved by someone else"):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(status=BusinessStatus.PAUSED),
        )

    stored = repo.get(business.id)
    assert stored is not None
    assert stored.status is BusinessStatus.LIVE
    # "Nothing changes": the live business keeps its voice agent.
    assert testbed.voice_agent_removals.business_ids == []


def test_a_status_switch_with_invalid_contacts_changes_nothing() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    make_live(testbed, business.id)

    with pytest.raises(ValidationFailedError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(
                status=BusinessStatus.PAUSED,
                manager_contacts=[contact(ManagerContactChannel.TELEGRAM, "@manager")],
            ),
        )

    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.status is BusinessStatus.LIVE
    assert testbed.voice_agent_removals.business_ids == []

    paused = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(status=BusinessStatus.PAUSED),
    )
    assert paused.status is BusinessStatus.PAUSED
    with pytest.raises(ValidationFailedError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(
                status=BusinessStatus.LIVE,
                manager_contacts=[contact(ManagerContactChannel.TELEGRAM, "@manager")],
            ),
        )

    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.status is BusinessStatus.PAUSED
    assert testbed.assistant_resumptions.business_ids == []


def test_a_member_invite_racing_a_settings_save_keeps_both(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    base_revision = int(business.revision)
    invite_staff = testbed.invite_staff
    find_or_create_user = invite_staff._find_or_create_user  # pyright: ignore[reportPrivateUsage]

    def settings_saved_meanwhile(*args: object) -> UserDocument:
        # Another owner saves the settings after the invite read the business.
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(
                expected_revision=BusinessRevision(base_revision),
                city=CityName("Berlin"),
            ),
        )
        return find_or_create_user(*args)  # type: ignore[arg-type]

    monkeypatch.setattr(invite_staff, "_find_or_create_user", settings_saved_meanwhile)

    invite_staff.run(
        InviteStaffCommand(
            user_id=owner_id,
            business_id=business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(GERMANY_MOBILE)
            ),
        )
    )

    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.city == "Berlin"
    assert len(stored.members) == 2
    assert stored.revision == base_revision + 2
