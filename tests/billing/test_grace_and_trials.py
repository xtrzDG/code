from typing import cast

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    CancelSubscriptionCommand,
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.billing_settings import (
    GEORGIA,
    ITALY,
    MICROSECONDS_PER_DAY,
    CountryPreset,
)
from tests.billing.billing_testbed import BillingTestbed


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


def test_paying_long_after_a_missed_renewal_buys_service_from_today() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    pay_open_invoices(testbed, owner, business)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    old_period_end = testbed.subscription(business.id).period_end
    testbed.clock.move_to(old_period_end)
    testbed.clock.advance(days=2)
    enforce(testbed)
    [stale] = [
        invoice
        for invoice in testbed.invoices(business.id)
        if invoice.status is InvoiceStatus.ISSUED
    ]
    testbed.clock.advance(days=8)
    enforce(testbed)
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    testbed.clock.advance(days=63)

    pay_open_invoices(testbed, owner, business, payment_id=7)

    today = testbed.clock.now()
    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start <= today < subscription.period_end
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    stored_stale = testbed.invoice_repo.get(business.id, stale.id)
    assert stored_stale is not None
    assert stored_stale.status is InvoiceStatus.VOID
    recurring = cast(
        dict[str, object], testbed.flitt.checkout_orders[-1]["recurring_data"]
    )
    assert str(recurring["start_time"]) >= str(
        to_local_calendar_day(today, business.timezone)
    )
    assert enforce(testbed) == 0
    assert testbed.business(business.id).service_mode is ServiceMode.FULL


def test_paying_a_trial_long_after_it_ended_restores_full_service() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    testbed.clock.advance(days=40)
    enforce(testbed)
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY

    pay_open_invoices(testbed, owner, business)

    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start <= testbed.clock.now() < subscription.period_end
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    paid = [
        invoice
        for invoice in testbed.invoices(business.id)
        if invoice.status is InvoiceStatus.PAID
    ]
    assert sorted(invoice.kind for invoice in paid) == [
        InvoiceKind.SERVICE_PERIOD,
        InvoiceKind.SETUP_FEE,
    ]


def test_a_cancelled_subscription_keeps_the_month_paid_ahead_in_the_trial() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    pay_open_invoices(testbed, owner, business)
    testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
    )
    [paid_month] = [
        invoice
        for invoice in testbed.invoices(business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    ]
    testbed.clock.advance(days=14, hours=1)

    end_trial(testbed)
    enforce(testbed)

    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    assert testbed.notifier.sent == []
    testbed.clock.move_to(paid_month.period_end)
    testbed.clock.advance(hours=-1)
    enforce(testbed)
    assert testbed.business(business.id).service_mode is ServiceMode.FULL

    testbed.clock.advance(hours=2)
    assert enforce(testbed) == 1
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    [(_, text)] = testbed.notifier.sent
    assert "Trattoria" in str(text)


def test_a_live_business_without_a_subscription_only_takes_requests() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)
    business.status = BusinessStatus.LIVE
    testbed.business_repo.save(business)

    assert enforce(testbed) == 1
    assert enforce(testbed) == 0
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY


def test_the_grace_job_keeps_an_owner_edit_made_while_it_runs() -> None:
    testbed = BillingTestbed()
    _, first = start_trial(testbed)
    _, second = start_trial(testbed, ITALY)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    testbed.clock.advance(days=8)
    deliver = testbed.notifier.notify

    def rename_second_while_notifying(
        contact: ManagerContact,
        text: MessageText,
    ) -> bool:
        stored = testbed.business(second.id)
        if str(stored.name) != "Renamed meanwhile":
            stored.name = BusinessName("Renamed meanwhile")
            testbed.business_repo.save(stored)

        return deliver(contact, text)

    testbed.notifier.notify = rename_second_while_notifying  # type: ignore[method-assign]

    assert enforce(testbed) == 2

    current = testbed.business(second.id)
    assert str(current.name) == "Renamed meanwhile"
    assert current.service_mode is ServiceMode.LEADS_ONLY
    assert testbed.business(first.id).service_mode is ServiceMode.LEADS_ONLY


def test_unpaid_overage_makes_the_subscription_past_due() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    pay_open_invoices(testbed, owner, business)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    period = testbed.subscription(business.id)
    testbed.record_usage(
        business.id,
        UsageKind.VOICE_SECONDS,
        500 * 60,
        occurred_at=period.period_start,
    )
    testbed.clock.move_to(period.period_end)
    testbed.clock.advance(hours=1)
    order = testbed.payment_order_repo.list_by_business(business.id)[0]
    testbed.deliver_flitt_callback(
        {
            **testbed.callback_parameters(
                order, "approved", payment_id=2, amount=51700
            ),
            "order_id": f"{order.id}_2",
            "parent_order_id": str(order.id),
        }
    )

    assert testbed.run_job(testbed.invoice_usage_overage, "invoice_usage_overage") == 1
    enforce(testbed)

    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    testbed.clock.advance(days=7, hours=1)
    enforce(testbed)
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY

    pay_open_invoices(testbed, owner, business, payment_id=3)

    assert testbed.subscription(business.id).status is SubscriptionStatus.ACTIVE
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    assert testbed.flitt.stopped_orders == [str(order.id)]
    assert enforce(testbed) == 0
