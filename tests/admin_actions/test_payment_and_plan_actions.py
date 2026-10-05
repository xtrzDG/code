"""
A bank transfer or cash recorded by hand pays an invoice as a card would;
a plan set by hand bills the next period at the price book's price; the
done-for-you setup is marked done.
"""

import pytest

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    ManualPaymentMethod,
    OnboardingRequestStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import OnboardingRequestDocument
from app.schemas.dto.admin_actions import (
    CompleteOnboardingCommand,
    OverridePlanBody,
    OverridePlanCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.utilities.billing.onboarding_keys import derive_onboarding_request_id
from tests.admin_actions.action_steps import mark_paid, override
from tests.admin_actions.action_world import REASON, ActionWorld
from tests.billing.grace_steps import end_trial, enforce


def ended_unpaid(world: ActionWorld) -> None:
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    world.testbed.clock.advance(days=7, hours=1)
    enforce(world.testbed)


def test_a_bank_transfer_pays_the_period_and_brings_full_service_back() -> None:
    world = ActionWorld()
    ended_unpaid(world)
    period = next(
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    )

    receipt = mark_paid(world, world.accountant, period.id)

    stored = world.testbed.invoice_repo.get(world.business.id, period.id)
    assert stored is not None and stored.status is InvoiceStatus.PAID
    assert stored.paid_at == world.testbed.clock.now()
    assert stored.manual_payment is not None
    assert stored.manual_payment.method is ManualPaymentMethod.BANK_TRANSFER
    assert str(stored.manual_payment.reference) == "TBC #1"
    assert stored.manual_payment.recorded_by == world.accountant.id
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.grace_until is None
    assert world.client().service_mode is ServiceMode.FULL
    assert ProductEventName.SUBSCRIBED in world.testbed.product_events.names()
    assert receipt.action is AuditAction.ADMIN_INVOICE_MARKED_PAID
    with pytest.raises(ConflictError, match="open invoice"):
        mark_paid(world, world.accountant, period.id)


def test_an_unknown_invoice_is_not_found() -> None:
    world = ActionWorld()

    with pytest.raises(NotFoundError):
        mark_paid(world, world.founder)


def test_a_plan_set_by_hand_bills_the_next_period_at_its_price() -> None:
    world = ActionWorld()
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    old_period = next(
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    )

    override(world, world.founder)

    subscription = world.testbed.subscription(world.business.id)
    assert (subscription.plan_key, subscription.billing_period) == (
        PlanKey.CHAT,
        BillingPeriod.MONTHLY,
    )
    assert subscription.price_minor != old_period.amount_minor
    assert world.client().plan_key is PlanKey.CHAT
    voided = world.testbed.invoice_repo.get(world.business.id, old_period.id)
    assert voided is not None and voided.status is InvoiceStatus.VOID
    [changed] = world.testbed.product_events.named(ProductEventName.PLAN_CHANGED)
    assert changed.properties.previous_plan_key is PlanKey.VOICE_AND_CHAT
    assert world.testbed.voice_agent_removals.business_ids == [world.business.id]
    with pytest.raises(ConflictError, match="already"):
        world.override_plan.run(
            OverridePlanCommand(
                user_id=world.founder.id,
                business_id=world.business.id,
                body=OverridePlanBody(plan_key=PlanKey.CHAT, reason=REASON),
            )
        )


def test_the_done_for_you_setup_is_marked_done_once() -> None:
    world = ActionWorld()
    command = CompleteOnboardingCommand(
        user_id=world.accountant.id, business_id=world.business.id
    )
    with pytest.raises(NotFoundError):
        world.complete_onboarding.run(command)

    world.testbed.onboarding_request_repo.open_once(
        OnboardingRequestDocument(
            id=derive_onboarding_request_id(world.business.id),
            business_id=world.business.id,
            requested_by=world.owner.id,
            plan_key=PlanKey.VOICE_AND_CHAT,
            requested_at=world.testbed.clock.now(),
        )
    )

    receipt = world.complete_onboarding.run(command)

    request = world.testbed.onboarding_request_repo.get_by_business(world.business.id)
    assert request is not None and request.status is OnboardingRequestStatus.DONE
    assert receipt.action is AuditAction.UPDATE
    with pytest.raises(ConflictError):
        world.complete_onboarding.run(command)
