import pytest

from app.schemas.constants.billing import BillingPeriod, PlanKey, SubscriptionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import (
    BusinessQuery,
    BusinessSettingsChanges,
    BusinessView,
    InviteStaffCommand,
    InviteStaffRequest,
    ManagerContactInput,
    UpdateBusinessSettingsCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    InvalidPhoneNumberError,
    NotFoundError,
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.constrained_integers import (
    BusinessRevision,
    RecordingRetentionDays,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import (
    BusinessName,
    CityName,
    RawManagerContactAddress,
)
from app.schemas.typings.handoffs.strings import ManagerName
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


def georgian_restaurant(testbed: AccountsTestbed) -> tuple[UserId, BusinessDocument]:
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    return owner.user.id, testbed.create_restaurant(owner.user.id, "Sakhli")


def update(
    testbed: AccountsTestbed,
    user_id: UserId,
    business_id: BusinessId,
    changes: BusinessSettingsChanges,
) -> BusinessView:
    return testbed.update_business_settings.run(
        UpdateBusinessSettingsCommand(
            user_id=user_id,
            business_id=business_id,
            changes=changes,
        )
    )


def contact(
    channel: ManagerContactChannel,
    address: str,
    language: str | None = None,
) -> ManagerContactInput:
    return ManagerContactInput(
        name=ManagerName("Nino"),
        channel=channel,
        address=RawManagerContactAddress(address),
        language=None if language is None else LanguageTag(language),
    )


def test_plan_of_a_subscribed_business_is_changed_in_billing_only() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    now = testbed.clock.now_microseconds()
    testbed.subscription_repo.save(
        SubscriptionDocument(
            business_id=business.id,
            plan_key=business.plan_key,
            billing_period=BillingPeriod.MONTHLY,
            price_minor=MoneyAmountMinor(51_700),
            currency_code=CurrencyCode("GEL"),
            status=SubscriptionStatus.TRIALING,
            period_start=now,
            period_end=now,
        )
    )

    unchanged = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(plan_key=business.plan_key, city=CityName("Kutaisi")),
    )
    with pytest.raises(ConflictError, match="change it in billing"):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(plan_key=PlanKey.PLUS),
        )

    assert unchanged.plan_key is business.plan_key
    assert unchanged.city == "Kutaisi"
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.plan_key is business.plan_key


def test_owner_changes_profile_settings_and_others_stay() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    testbed.clock.advance(10)

    updated = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            name=BusinessName("Sakhli Batumi"),
            city=CityName("Batumi"),
            plan_key=PlanKey.PLUS,
            recording_retention_days=RecordingRetentionDays(30),
        ),
    )

    assert updated.name == "Sakhli Batumi"
    assert updated.city == "Batumi"
    assert updated.plan_key is PlanKey.PLUS
    assert updated.recording_retention_days == 30
    assert updated.timezone == "Asia/Tbilisi"
    assert updated.languages == ["ka", "ru", "en"]
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.updated_at == testbed.clock.now_microseconds()
    assert stored.created_at == business.created_at

    cleared = update(
        testbed, owner_id, business.id, BusinessSettingsChanges(city=CityName(""))
    )
    assert cleared.city is None


def test_time_zone_must_exist() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)

    moved = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            timezone=TimezoneName("America/Argentina/Buenos_Aires")
        ),
    )
    assert moved.timezone == "America/Argentina/Buenos_Aires"

    with pytest.raises(ValidationFailedError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(timezone=TimezoneName("Asia/Atlantis")),
        )


def test_language_changes_keep_the_default_inside_the_list() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)

    without_georgian = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            languages=[LanguageTag("en"), LanguageTag("he"), LanguageTag("ar")]
        ),
    )
    assert without_georgian.languages == ["en", "he", "ar"]
    assert without_georgian.default_language == "en"

    hebrew_default = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            default_language=LanguageTag("he"),
            owner_language=LanguageTag("ru"),
        ),
    )
    assert hebrew_default.default_language == "he"
    assert hebrew_default.owner_language == "ru"

    kept_default = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(languages=[LanguageTag("ar"), LanguageTag("he")]),
    )
    assert kept_default.default_language == "he"

    with pytest.raises(ValidationFailedError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(default_language=LanguageTag("ka")),
        )

    with pytest.raises(UnsupportedLanguageError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(owner_language=LanguageTag("xh")),
        )


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
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    admin = UserDocument(
        login_method=LoginMethod.EMAIL,
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
