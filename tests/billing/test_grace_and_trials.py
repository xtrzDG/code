from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    CancelSubscriptionCommand,
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from tests.billing.billing_testbed import (
    GEORGIA,
    ITALY,
    MICROSECONDS_PER_DAY,
    BillingTestbed,
    CountryPreset,
)


def start_trial(
    testbed: BillingTestbed,
    country: CountryPreset = GEORGIA,
) -> tuple[UserDocument, BusinessDocument]:
    owner = (
        testbed.add_user(phone_number="+995599123456")
        if country is GEORGIA
        else testbed.add_user(email="owner@example.it", display_name="Giulia")
    )
    business = testbed.add_business(owner, country, name="Trattoria")
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(),
        )
    )
    return owner, business


def pay_open_invoices(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
    payment_id: int = 1,
) -> None:
    session = testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartCheckoutRequest(),
        )
    )
    order = testbed.payment_order_repo.get(session.payment_order_id)
    assert order is not None
    testbed.deliver_flitt_callback(
        testbed.callback_parameters(order, "approved", payment_id=payment_id)
    )


def end_trial(testbed: BillingTestbed) -> int:
    return testbed.run_job(testbed.end_trials, "end_trials")


def enforce(testbed: BillingTestbed) -> int:
    return testbed.run_job(testbed.enforce_grace_periods, "enforce_grace_periods")


def test_running_trials_are_left_alone() -> None:
    testbed = BillingTestbed()
    start_trial(testbed)
    testbed.clock.advance(days=13)

    assert end_trial(testbed) == 0
    assert enforce(testbed) == 0
    assert testbed.notifier.sent == []


def test_unpaid_trial_becomes_past_due_with_a_bill_and_a_notice() -> None:
    testbed = BillingTestbed()
    _, business = start_trial(testbed)
    trial_end = testbed.subscription(business.id).period_end
    testbed.clock.advance(days=14, hours=1)

    assert end_trial(testbed) == 1
    assert end_trial(testbed) == 0

    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    assert subscription.grace_until is not None
    assert int(subscription.grace_until) - int(testbed.clock.now()) == (
        7 * MICROSECONDS_PER_DAY
    )
    first_period, setup_fee = testbed.invoices(business.id)
    assert setup_fee.kind is InvoiceKind.SETUP_FEE
    assert first_period.kind is InvoiceKind.SERVICE_PERIOD
    assert first_period.period_start == trial_end
    assert {setup_fee.status, first_period.status} == {InvoiceStatus.ISSUED}
    [(contact, text)] = testbed.notifier.sent
    assert contact.channel is ManagerContactChannel.WHATSAPP
    assert str(text).startswith("Trattoria: უფასო საცდელი პერიოდი დასრულდა.")
    assert "960,00\xa0₾" in str(text)
    assert testbed.business(business.id).service_mode is ServiceMode.FULL


def test_grace_period_ends_in_leads_only_and_payment_restores_full_service() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)

    testbed.clock.advance(days=6)
    assert enforce(testbed) == 0
    assert testbed.business(business.id).service_mode is ServiceMode.FULL

    testbed.clock.advance(days=1, hours=1)
    assert enforce(testbed) == 1
    assert enforce(testbed) == 0
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    assert len(testbed.notifier.sent) == 2
    assert "მხოლოდ მოთხოვნებს იღებს" in str(testbed.notifier.sent[-1][1])

    pay_open_invoices(testbed, owner, business)

    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.grace_until is None
    assert subscription.period_start <= testbed.clock.now() < subscription.period_end
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    assert {invoice.status for invoice in testbed.invoices(business.id)} == {
        InvoiceStatus.PAID
    }


def test_missed_renewal_becomes_past_due_after_a_day() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed, ITALY)
    pay_open_invoices(testbed, owner, business)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    period_end = testbed.subscription(business.id).period_end

    testbed.clock.move_to(period_end)
    testbed.clock.advance(hours=12)
    assert enforce(testbed) == 0

    testbed.clock.advance(hours=13)
    assert enforce(testbed) == 1

    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    missed = testbed.invoices(business.id)[-1]
    assert missed.status is InvoiceStatus.ISSUED
    assert missed.period_start == period_end
    [(contact, text)] = testbed.notifier.sent
    assert contact.channel is ManagerContactChannel.EMAIL
    assert str(contact.name) == "Giulia"
    assert str(contact.language) == "it"
    assert str(text) == (
        "Trattoria: the payment of €175.00 for the new period has not arrived. "
        "Please pay in Billing. The assistant keeps full service until "
        "November 23, 2026; after that it will only take requests."
    )


def test_renewal_paid_ahead_moves_the_period_on_time() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed, ITALY)
    pay_open_invoices(testbed, owner, business)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    subscription = testbed.subscription(business.id)
    order = testbed.payment_order_repo.list_by_business(business.id)[0]
    testbed.clock.move_to(subscription.period_end)
    testbed.clock.advance(hours=-3)
    testbed.deliver_flitt_callback(
        testbed.callback_parameters(order, "approved", payment_id=2, amount=17500)
    )
    assert testbed.subscription(business.id).period_end == subscription.period_end

    testbed.clock.advance(hours=4)
    assert enforce(testbed) == 1

    moved = testbed.subscription(business.id)
    assert moved.status is SubscriptionStatus.ACTIVE
    assert moved.period_start == subscription.period_end
    assert testbed.notifier.sent == []


def test_cancelled_subscription_takes_requests_only_after_its_period() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed, ITALY)
    testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
    )

    testbed.clock.advance(days=13)
    assert enforce(testbed) == 0

    testbed.clock.advance(days=2)
    assert enforce(testbed) == 1
    assert enforce(testbed) == 0
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    [(_, text)] = testbed.notifier.sent
    assert "the subscription has ended" in str(text)


def test_paid_subscription_still_in_leads_only_returns_to_full_service() -> None:
    testbed = BillingTestbed()
    _, business = start_trial(testbed)
    stored = testbed.business(business.id)
    stored.service_mode = ServiceMode.LEADS_ONLY
    testbed.business_repo.save(stored)

    assert enforce(testbed) == 1
    assert testbed.business(business.id).service_mode is ServiceMode.FULL


def test_past_due_without_a_deadline_gets_one() -> None:
    testbed = BillingTestbed()
    _, business = start_trial(testbed)
    subscription = testbed.subscription(business.id)
    subscription.status = SubscriptionStatus.PAST_DUE
    testbed.subscription_repo.save(subscription)

    assert enforce(testbed) == 1
    assert testbed.subscription(business.id).grace_until is not None


def test_jobs_continue_when_notices_cannot_be_delivered() -> None:
    testbed = BillingTestbed()
    _, business = start_trial(testbed)
    testbed.notifier.is_delivering = False
    testbed.clock.advance(days=22)

    assert end_trial(testbed) == 1
    assert testbed.subscription(business.id).status is SubscriptionStatus.PAST_DUE
    assert len(testbed.notifier.sent) == 1


def test_businesses_without_subscription_are_skipped() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    testbed.add_business(owner, ITALY)

    assert end_trial(testbed) == 0
    assert enforce(testbed) == 0
