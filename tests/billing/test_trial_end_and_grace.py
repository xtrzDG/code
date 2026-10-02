"""Ending trials and enforcing grace periods: past due, leads only, full service."""

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus, SubscriptionStatus
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import MessageText
from tests.billing.billing_settings import ITALY, MICROSECONDS_PER_DAY
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.grace_steps import end_trial, enforce, pay_open_invoices, start_trial


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
