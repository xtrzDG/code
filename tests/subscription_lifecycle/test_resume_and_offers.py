"""Ending a pause early, and taking an offer instead of cancelling."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingCreditKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
    SubscriptionEventKind,
)
from app.schemas.dto.billing_cabinet import ChangePlanCommand, ChangePlanRequest
from app.schemas.dto.subscription_lifecycle import (
    AcceptRetentionOfferCommand,
    AcceptRetentionOfferRequest,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    PauseMonthCount,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.billing.grace_steps import pay_open_invoices
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld
from tests.subscription_lifecycle.pause_steps import (
    pause,
    pause_invoices,
    reach_pause_start,
    resume,
)


def accept(
    world: LifecycleWorld,
    owner_id: UserId,
    business_id: BusinessId,
    reason: CancellationReason,
    kind: RetentionOfferKind,
    months: int | None = None,
) -> None:
    world.accept_offer.run(
        AcceptRetentionOfferCommand(
            user_id=owner_id,
            business_id=business_id,
            request=AcceptRetentionOfferRequest(
                reason=reason,
                kind=kind,
                pause_months=None if months is None else PauseMonthCount(months),
            ),
        )
    )


def test_resuming_before_the_start_calls_the_pause_off() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=2)

    overview = resume(world, owner, business)

    assert overview.subscription is not None
    assert overview.subscription.pause_starts_at is None
    assert overview.subscription.status is SubscriptionStatus.ACTIVE
    last = world.steps(business)[-1]
    assert last.kind is SubscriptionEventKind.RESUMED
    assert last.pause_until == last.pause_starts_at
    assert world.lifecycle_of(business).pause.max_months == 4


def test_resuming_an_unpaid_pause_month_brings_full_service_back_now() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=3)
    reach_pause_start(world, business)
    world.clock.advance(days=5)

    resume(world, owner, business)

    resumed = world.current(business)
    assert resumed.status is SubscriptionStatus.ACTIVE
    assert resumed.period_end == world.clock.now()
    assert world.business(business.id).service_mode is ServiceMode.FULL
    assert pause_invoices(world, business)[0].status is InvoiceStatus.VOID


def test_resuming_a_paid_pause_month_ends_the_pause_with_that_month() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=3)
    reach_pause_start(world, business)
    pay_open_invoices(world, owner, business, payment_id=9)
    month_end = world.current(business).period_end

    resume(world, owner, business)

    still_paused = world.current(business)
    assert still_paused.status is SubscriptionStatus.PAUSED
    assert still_paused.pause_until == month_end
    world.clock.move_to(Microseconds(int(month_end) + 1))
    world.run_pause_job()
    assert world.current(business).status is SubscriptionStatus.ACTIVE
    assert len(pause_invoices(world, business)) == 1


def test_there_is_nothing_to_resume_without_a_pause() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()

    with pytest.raises(ConflictError):
        resume(world, owner, business)


def test_a_paused_subscription_keeps_its_plan_until_it_is_resumed() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=1)
    reach_pause_start(world, business)

    with pytest.raises(ConflictError):
        world.change_plan.run(
            ChangePlanCommand(
                user_id=owner.id,
                business_id=business.id,
                request=ChangePlanRequest(
                    plan_key=PlanKey.CHAT,
                    billing_period=world.current(business).billing_period,
                ),
            )
        )


def test_taking_the_pause_offer_schedules_the_pause() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()

    accept(
        world,
        owner.id,
        business.id,
        CancellationReason.SEASONAL_BREAK,
        RetentionOfferKind.PAUSE,
        months=3,
    )

    assert world.current(business).pause_until is not None
    last = world.steps(business)[-1]
    assert last.kind is SubscriptionEventKind.OFFER_ACCEPTED
    assert last.cancellation_reason is CancellationReason.SEASONAL_BREAK
    assert last.offer_kind is RetentionOfferKind.PAUSE and last.pause_months == 3


def test_the_pause_offer_needs_its_months() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()

    with pytest.raises(ValidationFailedError):
        accept(
            world,
            owner.id,
            business.id,
            CancellationReason.SEASONAL_BREAK,
            RetentionOfferKind.PAUSE,
        )
    assert world.current(business).pause_until is None


def test_taking_the_downgrade_moves_to_the_next_cheaper_plan() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()

    accept(
        world,
        owner.id,
        business.id,
        CancellationReason.TOO_EXPENSIVE,
        RetentionOfferKind.DOWNGRADE,
    )

    subscription = world.current(business)
    assert subscription.plan_key is PlanKey.CHAT
    assert int(subscription.price_minor) == 29300
    assert subscription.status is SubscriptionStatus.ACTIVE


def test_taking_the_credit_puts_it_on_the_ledger_once() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()

    accept(
        world,
        owner.id,
        business.id,
        CancellationReason.ANSWER_QUALITY,
        RetentionOfferKind.CREDIT,
    )

    [line] = world.billing_credit_repo.list_by_business(business.id)
    assert line.kind is BillingCreditKind.GRANTED
    assert int(line.amount_minor) == 25850
    assert line.save_offer_for == world.current(business).id
    with pytest.raises(ConflictError):
        accept(
            world,
            owner.id,
            business.id,
            CancellationReason.MISSING_FEATURE,
            RetentionOfferKind.CREDIT,
        )


def test_an_offer_the_reason_does_not_get_is_refused() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()

    with pytest.raises(ConflictError):
        accept(
            world,
            owner.id,
            business.id,
            CancellationReason.CLOSING_BUSINESS,
            RetentionOfferKind.CREDIT,
        )
    with pytest.raises(ConflictError):
        accept(
            world,
            owner.id,
            business.id,
            CancellationReason.SEASONAL_BREAK,
            RetentionOfferKind.DOWNGRADE,
        )
    assert world.steps(business) == []
