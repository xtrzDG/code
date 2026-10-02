"""Changing the business profile: plan, time zone and languages."""

import pytest

from app.schemas.constants.billing import BillingPeriod, PlanKey, SubscriptionStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.dto.businesses import BusinessSettingsChanges
from app.schemas.exceptions.application_errors import (
    ConflictError,
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.constrained_integers import RecordingRetentionDays
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from tests.businesses.business_settings_steps import georgian_restaurant, update
from tests.users.accounts_testbed import build_accounts_testbed


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
