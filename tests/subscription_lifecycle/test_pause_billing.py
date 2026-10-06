"""A seasonal pause: billed at its share of the price, leads only, back on time."""

from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.subscription_lifecycle import SubscriptionEventKind
from app.utilities.billing.billing_periods import (
    add_calendar_months,
    to_local_calendar_day,
)
from tests.billing.grace_steps import enforce, pay_open_invoices
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld
from tests.subscription_lifecycle.pause_steps import (
    HOUR_MICROSECONDS,
    pause,
    pause_invoices,
    reach_pause_start,
    reach_period_end,
)


def test_a_pause_starts_when_the_paid_period_ends_and_stops_full_price_charges() -> (
    None
):
    world = LifecycleWorld()
    owner, business = world.paying_business()
    paid_until = world.current(business).period_end
    reference = world.current(business).provider_reference
    assert reference is not None

    overview = pause(world, owner, business, months=2)

    assert overview.subscription is not None
    assert overview.subscription.pause_starts_at == paid_until
    assert overview.subscription.pause_until == add_calendar_months(
        paid_until, 2, business.timezone
    )
    assert overview.subscription.has_auto_debit is False
    assert world.flitt.stopped_orders == [str(reference)]
    assert overview.subscription.status is SubscriptionStatus.ACTIVE
    # Full service until the paid period ends.
    assert world.run_pause_job() == 0
    assert world.business(business.id).service_mode is ServiceMode.FULL
    scheduled = [s for s in world.steps(business) if s.kind.value == "pause_scheduled"]
    assert len(scheduled) == 1 and scheduled[0].pause_months == 2


def test_billing_while_paused_bills_each_month_at_fifteen_percent() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=2)

    reach_pause_start(world, business)

    paused = world.current(business)
    assert paused.status is SubscriptionStatus.PAUSED
    assert world.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    [first_month] = pause_invoices(world, business)
    assert first_month.status is InvoiceStatus.ISSUED
    assert int(first_month.subtotal_minor or first_month.amount_minor) == 7755
    assert first_month.period_start == paused.pause_starts_at
    assert first_month.period_end == paused.period_end
    assert any(
        "seasonal pause, requests only" in str(line.text)
        for line in first_month.line_texts
    )
    # The owner language of the business is Georgian.
    assert any("სეზონური პაუზა დაიწყო" in text for text in world.notifier.texts())
    assert [s.kind for s in world.steps(business)][-1] is (
        SubscriptionEventKind.PAUSE_STARTED
    )

    # The grace job keeps a pause to requests only and bills no renewal.
    world.clock.advance(days=3)
    enforce(world)
    assert world.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    assert len(world.invoices(business.id)) == len(world.open_invoices_of(business)) + 1

    reach_period_end(world, business)
    assert world.run_pause_job() == 1
    months = pause_invoices(world, business)
    assert len(months) == 2
    assert months[1].period_start == months[0].period_end
    # Running the job again bills nothing twice.
    world.run_pause_job()
    assert len(pause_invoices(world, business)) == 2


def test_a_paid_pause_month_keeps_the_pause_and_automatic_charges_start_after_it() -> (
    None
):
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=3)
    reach_pause_start(world, business)
    pause_until = world.current(business).pause_until
    assert pause_until is not None

    pay_open_invoices(world, owner, business, payment_id=7)

    recurring = world.flitt.checkout_orders[-1]["recurring_data"]
    assert isinstance(recurring, dict)
    assert recurring["start_time"] == str(
        to_local_calendar_day(pause_until, business.timezone)
    )
    paused = world.current(business)
    assert paused.status is SubscriptionStatus.PAUSED
    assert world.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    assert pause_invoices(world, business)[0].status is InvoiceStatus.PAID


def test_auto_resume_brings_full_service_back_when_the_pause_ends() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=1)
    reach_pause_start(world, business)
    pause_until = world.current(business).pause_until
    assert pause_until is not None

    world.clock.move_to(type(pause_until)(int(pause_until) + HOUR_MICROSECONDS))
    assert world.run_pause_job() == 1

    resumed = world.current(business)
    assert resumed.status is SubscriptionStatus.ACTIVE
    assert resumed.pause_starts_at is None and resumed.pause_until is None
    assert resumed.period_end == pause_until
    assert world.business(business.id).service_mode is ServiceMode.FULL
    assert any("სეზონური პაუზა დასრულდა" in text for text in world.notifier.texts())
    last = world.steps(business)[-1]
    assert last.kind is SubscriptionEventKind.RESUMED and last.actor_id is None
    assert last.pause_until == pause_until

    # Automatic charges are off: a day later the renewal is billed in full
    # with the plan's grace.
    world.clock.advance(days=1, hours=1)
    enforce(world)
    renewal = world.invoices(business.id)[-1]
    assert int(renewal.subtotal_minor or renewal.amount_minor) == 51700
    assert renewal.period_start == pause_until
    assert world.current(business).status is SubscriptionStatus.PAST_DUE
    assert world.business(business.id).service_mode is ServiceMode.FULL


def test_a_late_job_resumes_a_pause_that_ran_out_without_billing_its_months() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=2)
    reach_pause_start(world, business)
    pause_until = world.current(business).pause_until
    assert pause_until is not None

    world.clock.move_to(type(pause_until)(int(pause_until) + 5 * HOUR_MICROSECONDS))
    world.run_pause_job()

    assert world.current(business).status is SubscriptionStatus.ACTIVE
    assert len(pause_invoices(world, business)) == 1
