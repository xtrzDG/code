import pytest

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewQuery,
    CancelSubscriptionCommand,
    ChangePlanCommand,
    ChangePlanRequest,
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.billing_testbed import (
    GEORGIA,
    ISRAEL,
    ITALY,
    JAPAN,
    MICROSECONDS_PER_DAY,
    USA,
    BillingTestbed,
    CountryPreset,
    PriceBookPlanRegistry,
)


def start_trial(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
    plan_key: PlanKey | None = None,
    billing_period: BillingPeriod = BillingPeriod.MONTHLY,
    language: str | None = None,
) -> BillingOverview:
    return testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(plan_key=plan_key, billing_period=billing_period),
            display_language=None if language is None else LanguageTag(language),
        )
    )


def change_plan(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
    plan_key: PlanKey,
    billing_period: BillingPeriod,
) -> BillingOverview:
    return testbed.change_plan.run(
        ChangePlanCommand(
            user_id=owner.id,
            business_id=business.id,
            request=ChangePlanRequest(plan_key=plan_key, billing_period=billing_period),
        )
    )


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


def test_change_plan_during_the_trial_reprices_at_once() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456")
    business = testbed.add_business(owner, GEORGIA)
    start_trial(testbed, owner, business)

    overview = change_plan(
        testbed,
        owner,
        business,
        PlanKey.PLUS,
        BillingPeriod.ANNUAL,
    )

    assert overview.subscription is not None
    assert overview.subscription.plan_key is PlanKey.PLUS
    assert overview.subscription.status is SubscriptionStatus.TRIALING
    assert int(overview.subscription.price.money.amount_minor) == 1051620
    assert overview.usage is not None
    assert int(overview.usage.included_voice_minutes) == 1000
    assert testbed.business(business.id).plan_key is PlanKey.PLUS
    assert testbed.flitt.stopped_orders == []


def test_changing_to_the_same_plan_changes_nothing() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456")
    business = testbed.add_business(owner, GEORGIA)
    start_trial(testbed, owner, business)
    before = testbed.subscription(business.id)

    change_plan(
        testbed,
        owner,
        business,
        PlanKey.VOICE_AND_CHAT,
        BillingPeriod.MONTHLY,
    )

    assert testbed.subscription(business.id) == before


def test_plan_changes_need_a_subscription_and_a_price() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)

    with pytest.raises(NotFoundError):
        change_plan(testbed, owner, business, PlanKey.PLUS, BillingPeriod.MONTHLY)

    with pytest.raises(NotFoundError):
        testbed.cancel_subscription.run(
            CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
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


def test_cancel_ends_the_trial_at_its_end_and_is_idempotent() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)
    start_trial(testbed, owner, business)
    command = CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)

    first = testbed.cancel_subscription.run(command)
    second = testbed.cancel_subscription.run(command)

    assert first.subscription is not None
    assert first.subscription.status is SubscriptionStatus.CANCELLED
    assert second == first
    assert all(
        invoice.status is InvoiceStatus.VOID
        for invoice in testbed.invoices(business.id)
    )


def test_switching_from_paid_annual_to_monthly_bills_no_setup_fee() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456", locale="ka")
    business = testbed.add_business(owner, GEORGIA)
    start_trial(testbed, owner, business, billing_period=BillingPeriod.ANNUAL)
    first = testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartCheckoutRequest(),
        )
    )
    order = testbed.payment_order_repo.get(first.payment_order_id)
    assert order is not None
    testbed.deliver_flitt_callback(testbed.callback_parameters(order, "approved"))
    testbed.clock.advance(days=300)

    change_plan(testbed, owner, business, PlanKey.VOICE_AND_CHAT, BillingPeriod.MONTHLY)
    session = testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartCheckoutRequest(),
        )
    )

    assert session.amount.text == "517,00\xa0₾"
    assert all(
        invoice.kind is not InvoiceKind.SETUP_FEE
        for invoice in testbed.invoices(business.id)
    )
