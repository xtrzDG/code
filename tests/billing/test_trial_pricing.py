"""Starting the trial: local prices, the annual discount, who may start it."""

import pytest

from app.schemas.constants.billing import BillingPeriod, PlanKey, SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_cabinet import (
    BillingOverviewQuery,
    CancelSubscriptionCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.billing_registries import PriceBookPlanRegistry
from tests.billing.billing_settings import (
    GEORGIA,
    ISRAEL,
    ITALY,
    JAPAN,
    MICROSECONDS_PER_DAY,
    USA,
    CountryPreset,
)
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.plan_steps import change_plan, start_trial


def test_trial_in_georgia_is_priced_in_lari_from_the_price_book() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456", locale="ka")
    business = testbed.add_business(owner, GEORGIA, plan_key=PlanKey.CHAT)

    overview = start_trial(testbed, owner, business, plan_key=PlanKey.VOICE_AND_CHAT)

    assert overview.currency_code == "GEL"
    assert overview.display_language == "ka"
    assert overview.is_trial_available is False
    assert overview.invoices == []
    subscription = overview.subscription
    assert subscription is not None
    assert subscription.status is SubscriptionStatus.TRIALING
    assert subscription.plan_key is PlanKey.VOICE_AND_CHAT
    assert subscription.plan_name == "ხმა + ჩატი"
    assert int(subscription.price.money.amount_minor) == 51700
    assert subscription.price.text == "517,00\xa0₾"
    assert subscription.has_auto_debit is False
    assert subscription.trial_ends_at == subscription.period_end
    assert int(subscription.period_end) - int(subscription.period_start) == (
        14 * MICROSECONDS_PER_DAY
    )
    assert testbed.business(business.id).plan_key is PlanKey.VOICE_AND_CHAT


@pytest.mark.parametrize(
    ("country", "expected_text"),
    [
        (ITALY, "175,00\xa0€"),
        (USA, "€175.00"),
        (JAPAN, "€175.00"),
        (ISRAEL, "‏175.00\xa0‏€"),
    ],
)
def test_trial_elsewhere_is_priced_in_euro(
    country: CountryPreset,
    expected_text: str,
) -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, country)

    overview = start_trial(testbed, owner, business)

    assert overview.currency_code == "EUR"
    assert overview.subscription is not None
    assert int(overview.subscription.price.money.amount_minor) == 17500
    assert overview.subscription.price.text == expected_text


def test_trial_follows_a_local_price_book_in_any_currency() -> None:
    registry = PriceBookPlanRegistry(
        monthly_prices={(PlanKey.VOICE_AND_CHAT, "JPY"): 28333},
        setup_fees={(PlanKey.VOICE_AND_CHAT, "JPY"): 24000},
    )
    testbed = BillingTestbed(plan_registry=registry)
    owner = testbed.add_user(email="owner@example.jp", locale="ja")
    business = testbed.add_business(owner, JAPAN)

    monthly = start_trial(testbed, owner, business)
    annual = change_plan(
        testbed,
        owner,
        business,
        PlanKey.VOICE_AND_CHAT,
        BillingPeriod.ANNUAL,
    )

    assert monthly.subscription is not None
    assert monthly.subscription.price.text == "￥28,333"
    assert annual.subscription is not None
    assert int(annual.subscription.price.money.amount_minor) == 288997
    assert annual.subscription.billing_period is BillingPeriod.ANNUAL


def test_annual_trial_is_priced_with_the_annual_discount() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456")
    business = testbed.add_business(owner, GEORGIA)

    overview = start_trial(
        testbed,
        owner,
        business,
        plan_key=PlanKey.CHAT,
        billing_period=BillingPeriod.ANNUAL,
        language="ru",
    )

    assert overview.subscription is not None
    assert overview.subscription.plan_name == "Чат"
    assert overview.subscription.price.text == "2\xa0988,60\xa0GEL"


def test_the_trial_is_available_once_per_business() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)
    start_trial(testbed, owner, business)
    testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
    )

    with pytest.raises(ConflictError):
        start_trial(testbed, owner, business)


def test_only_owners_manage_billing() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    staff = testbed.add_user(email="staff@example.com")
    stranger = testbed.add_user(email="stranger@example.com")
    business = testbed.add_business(owner, ITALY, staff=[staff])

    with pytest.raises(AccessDeniedError):
        start_trial(testbed, staff, business)

    with pytest.raises(NotFoundError):
        start_trial(testbed, stranger, business)

    with pytest.raises(AccessDeniedError):
        testbed.get_overview.run(
            BillingOverviewQuery(user_id=staff.id, business_id=business.id)
        )


def test_overview_before_the_trial_offers_it_in_the_local_currency() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456")
    business = testbed.add_business(owner, GEORGIA)

    overview = testbed.get_overview.run(
        BillingOverviewQuery(
            user_id=owner.id,
            business_id=business.id,
            display_language=LanguageTag("en"),
        )
    )

    assert overview.is_trial_available is True
    assert overview.subscription is None
    assert overview.usage is None
    assert overview.currency_code == "GEL"
    assert overview.service_mode is ServiceMode.FULL


def test_overview_rejects_languages_without_locale_data() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)

    with pytest.raises(UnsupportedLanguageError):
        testbed.get_overview.run(
            BillingOverviewQuery(
                user_id=owner.id,
                business_id=business.id,
                display_language=LanguageTag("xx"),
            )
        )


def test_a_plan_without_trial_days_cannot_start_a_trial() -> None:
    class NoTrialRegistry(PriceBookPlanRegistry):
        def get(self, plan_key: PlanKey) -> PlanDefinition:
            plan = super().get(plan_key)
            return plan.model_copy(update={"trial_days": 0})

    testbed = BillingTestbed(plan_registry=NoTrialRegistry(monthly_prices={}))
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)

    with pytest.raises(ValidationFailedError):
        start_trial(testbed, owner, business)
