"""Subscribing without a trial: the first payment, unpaid periods, two pages."""

import pytest

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.client_health import ClientHealthIssue
from app.schemas.dto.admin import AdminClientsQuery
from app.schemas.dto.billing_cabinet import (
    BillingOverviewQuery,
    CheckoutSessionView,
    StartCheckoutCommand,
    StartCheckoutRequest,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.billing.billing_records import is_service_paid_for
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.billing_settings import CABINET_ORIGIN
from tests.billing.subscribe_world import World


def test_subscribing_without_a_trial_bills_setup_and_the_first_month_from_now() -> None:
    world = World()
    now = world.testbed.clock.now()

    session = world.subscribe(PlanKey.CHAT)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.INCOMPLETE
    assert subscription.plan_key is PlanKey.CHAT
    assert subscription.trial_ends_at is None
    assert str(subscription.currency_code) == "GEL"
    first_period, setup_fee = world.testbed.invoices(world.business.id)
    assert setup_fee.kind is InvoiceKind.SETUP_FEE
    assert first_period.kind is InvoiceKind.SERVICE_PERIOD
    assert first_period.period_start == now
    assert int(first_period.amount_minor) == int(subscription.price_minor)
    assert set(session.invoice_ids) == {setup_fee.id, first_period.id}
    sent = world.testbed.flitt.checkout_orders[0]
    assert sent["amount"] == int(setup_fee.amount_minor) + int(
        first_period.amount_minor
    )
    assert sent["response_url"] == f"{CABINET_ORIGIN}/billing"
    recurring = sent["recurring_data"]
    assert isinstance(recurring, dict)
    assert recurring["amount"] == int(subscription.price_minor)
    assert recurring["start_time"] == str(
        to_local_calendar_day(first_period.period_end, world.business.timezone)
    )
    business = world.testbed.business(world.business.id)
    assert business.plan_key is PlanKey.CHAT
    assert not is_service_paid_for(subscription, now)


def test_unpaid_subscription_shows_no_package_and_keeps_the_trial_on_offer() -> None:
    world = World()
    world.subscribe()

    overview = world.testbed.get_overview.run(
        BillingOverviewQuery(user_id=world.owner.id, business_id=world.business.id)
    )

    assert overview.subscription is not None
    assert overview.subscription.status is SubscriptionStatus.INCOMPLETE
    assert overview.usage is None
    assert overview.is_trial_available is True


def test_the_first_payment_activates_the_subscription_and_the_service() -> None:
    world = World()
    world.testbed.business_repo.save(
        world.business.model_copy(
            update={
                "status": BusinessStatus.LIVE,
                "service_mode": ServiceMode.LEADS_ONLY,
            }
        )
    )
    session = world.subscribe()

    world.pay(session)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == world.testbed.clock.now()
    assert str(subscription.provider_reference) == str(session.payment_order_id)
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL
    assert world.open_invoices() == []


def test_a_live_business_waiting_for_its_first_payment_only_takes_requests() -> None:
    world = World()
    world.testbed.business_repo.save(
        world.business.model_copy(update={"status": BusinessStatus.LIVE})
    )
    world.subscribe()

    world.testbed.run_job(world.testbed.enforce_grace_periods, "enforce_grace_periods")

    assert world.testbed.business(world.business.id).service_mode is (
        ServiceMode.LEADS_ONLY
    )


def test_subscribing_again_redates_the_unpaid_period_without_a_second_setup_fee() -> (
    None
):
    world = World()
    first = world.subscribe()
    world.testbed.clock.advance(days=3)

    second = world.subscribe()

    invoices = world.testbed.invoices(world.business.id)
    assert [invoice.kind for invoice in invoices].count(InvoiceKind.SETUP_FEE) == 1
    periods = [
        invoice for invoice in invoices if invoice.kind is InvoiceKind.SERVICE_PERIOD
    ]
    assert [invoice.status for invoice in periods] == [
        InvoiceStatus.VOID,
        InvoiceStatus.ISSUED,
    ]
    assert periods[1].period_start == world.testbed.clock.now()
    assert second.payment_order_id != first.payment_order_id
    assert len(second.invoice_ids) == 2


def test_starting_the_trial_after_an_unpaid_subscription_voids_its_bills() -> None:
    world = World()
    world.subscribe()

    world.start_trial()

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    assert subscription.trial_ends_at is not None
    assert world.open_invoices() == []
    with pytest.raises(ConflictError):
        world.start_trial()


def test_checkout_of_an_unpaid_subscription_still_works() -> None:
    world = World()
    world.subscribe()

    session = world.testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=StartCheckoutRequest(),
        )
    )

    assert len(session.invoice_ids) == 2


def test_the_admin_sees_a_first_payment_pending() -> None:
    world = World()
    admin = world.testbed.add_user(email="admin@example.com", is_platform_admin=True)
    world.subscribe()

    clients = world.testbed.list_clients.run(AdminClientsQuery(user_id=admin.id))

    summary = clients.items[0]
    assert summary.subscription_status is SubscriptionStatus.INCOMPLETE
    assert ClientHealthIssue.FIRST_PAYMENT_PENDING in summary.health_issues


def paid_service_periods(world: World) -> int:
    return len(
        [
            invoice
            for invoice in world.testbed.invoices(world.business.id)
            if invoice.kind is InvoiceKind.SERVICE_PERIOD
            and invoice.status is InvoiceStatus.PAID
        ]
    )


def refund_flags(world: World, *sessions: CheckoutSessionView) -> tuple[bool, ...]:
    flags: list[bool] = []
    for session in sessions:
        order = world.testbed.payment_order_repo.get(session.payment_order_id)
        assert order is not None
        flags.append(order.is_refund_due)
    return tuple(flags)


def test_paying_both_checkout_pages_flags_the_second_for_refund() -> None:
    # The owner returns before the webhook, sees "pay for this plan" again
    # and pays a second page for nearly the same month and the setup fee.
    world = World()
    first = world.subscribe()
    world.testbed.clock.advance(hours=1)
    second = world.subscribe()

    world.pay(first, payment_id=1)
    world.pay(second, payment_id=2)

    assert refund_flags(world, first, second) == (False, True)
    assert paid_service_periods(world) == 1
    assert world.open_invoices() == []


def test_paying_the_pages_in_reverse_order_still_books_one_month() -> None:
    world = World()
    first = world.subscribe()
    world.testbed.clock.advance(hours=1)
    second = world.subscribe()

    world.pay(second, payment_id=2)
    world.pay(first, payment_id=1)

    assert refund_flags(world, first, second) == (True, False)
    assert paid_service_periods(world) == 1
    assert world.open_invoices() == []


def test_paying_only_the_first_page_leaves_no_overlapping_month_due() -> None:
    world = World()
    first = world.subscribe()
    world.testbed.clock.advance(hours=1)
    world.subscribe()

    world.pay(first)

    assert refund_flags(world, first) == (False,)
    assert paid_service_periods(world) == 1
    assert world.open_invoices() == []


def test_a_page_paid_after_the_trial_started_books_no_month_inside_the_trial() -> None:
    world = World()
    first = world.subscribe()
    world.start_trial()

    world.pay(first)

    assert refund_flags(world, first) == (True,)
    assert paid_service_periods(world) == 0
