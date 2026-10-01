import json
from dataclasses import dataclass
from urllib.parse import urlencode

import pytest

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    CancelSubscriptionCommand,
    ChangePlanCommand,
    ChangePlanRequest,
    CheckoutSessionView,
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_strings import PaymentReturnUrl
from app.schemas.typings.billing.prefixed_id import PaymentOrderId, SubscriptionId
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.billing_testbed import (
    APP_BASE_URL,
    CABINET_ORIGIN,
    CHECKOUT_URL,
    GEORGIA,
    ITALY,
    BillingTestbed,
    CountryPreset,
    sign_flitt_callback,
)


@dataclass(frozen=True)
class PaidWorld:
    testbed: BillingTestbed
    owner: UserDocument
    business: BusinessDocument


def build_trial(
    country: CountryPreset = GEORGIA,
    billing_period: BillingPeriod = BillingPeriod.MONTHLY,
) -> PaidWorld:
    testbed = BillingTestbed()
    owner = (
        testbed.add_user(phone_number="+995599123456", locale="ka")
        if country is GEORGIA
        else testbed.add_user(email="owner@example.com")
    )
    business = testbed.add_business(owner, country)
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(billing_period=billing_period),
        )
    )
    return PaidWorld(testbed=testbed, owner=owner, business=business)


def checkout(world: PaidWorld, return_url: str | None = None) -> CheckoutSessionView:
    return world.testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=StartCheckoutRequest(
                return_url=None if return_url is None else PaymentReturnUrl(return_url)
            ),
        )
    )


def payment_order(
    world: PaidWorld, session: CheckoutSessionView
) -> PaymentOrderDocument:
    order = world.testbed.payment_order_repo.get(session.payment_order_id)
    assert order is not None
    return order


def pay(world: PaidWorld, session: CheckoutSessionView, payment_id: int = 1) -> None:
    order = payment_order(world, session)
    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved", payment_id=payment_id)
    )
    assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def build_active_subscription() -> tuple[PaidWorld, PaymentOrderDocument]:
    world = build_trial()
    session = checkout(world)
    pay(world, session)
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    return world, payment_order(world, session)


def test_checkout_during_the_trial_prepays_the_first_month_and_setup() -> None:
    world = build_trial()
    trial_end = world.testbed.subscription(world.business.id).period_end

    session = checkout(world)

    invoices = world.testbed.invoices(world.business.id)
    setup_fee, first_period = invoices
    assert setup_fee.kind is InvoiceKind.SETUP_FEE
    assert int(setup_fee.amount_minor) == 44300
    assert setup_fee.period_start == setup_fee.period_end
    assert first_period.kind is InvoiceKind.SERVICE_PERIOD
    assert first_period.period_start == trial_end
    assert int(first_period.amount_minor) == 51700
    assert all(invoice.status is InvoiceStatus.ISSUED for invoice in invoices)
    assert session.amount.text == "960,00\xa0₾"
    assert str(session.checkout_url) == CHECKOUT_URL
    assert set(session.invoice_ids) == {setup_fee.id, first_period.id}
    sent = world.testbed.flitt.checkout_orders[0]
    assert sent["amount"] == 96000
    assert sent["currency"] == "GEL"
    assert sent["lang"] == "ka"
    assert sent["order_desc"] == str(first_period.description)
    assert sent["recurring_data"] == {
        "every": 1,
        "period": "month",
        "amount": 51700,
        "start_time": str(
            to_local_calendar_day(first_period.period_end, world.business.timezone)
        ),
        "state": "y",
        "readonly": "y",
    }
    assert "response_url" not in sent
    order = payment_order(world, session)
    assert order.status is PaymentStatus.CREATED
    assert int(order.recurring_amount_minor) == 51700
    assert str(order.last_payment_reference) == "802345671"


def test_annual_checkout_includes_the_setup_fee_and_charges_yearly() -> None:
    world = build_trial(ITALY, BillingPeriod.ANNUAL)

    session = checkout(world)

    invoices = world.testbed.invoices(world.business.id)
    assert [invoice.kind for invoice in invoices] == [InvoiceKind.SERVICE_PERIOD]
    assert int(invoices[0].amount_minor) == 178500
    assert session.amount.text == "1.785,00\xa0€"
    recurring = world.testbed.flitt.checkout_orders[0]["recurring_data"]
    assert isinstance(recurring, dict)
    assert recurring["every"] == 12
    assert world.testbed.flitt.checkout_orders[0]["lang"] == "it"


@pytest.mark.parametrize(
    "return_url",
    [f"{CABINET_ORIGIN}/billing?paid=1", CABINET_ORIGIN, f"{APP_BASE_URL}/done"],
)
def test_return_page_on_an_allowed_origin_is_passed_on(return_url: str) -> None:
    world = build_trial()

    checkout(world, return_url)

    assert world.testbed.flitt.checkout_orders[0]["response_url"] == return_url


@pytest.mark.parametrize(
    "return_url",
    ["https://evil.example/billing", f"{CABINET_ORIGIN}.evil.example/billing"],
)
def test_return_page_elsewhere_is_refused(return_url: str) -> None:
    world = build_trial()

    with pytest.raises(ValidationFailedError):
        checkout(world, return_url)

    assert world.testbed.flitt.checkout_orders == []


def test_checkout_without_a_subscription_is_not_found() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)

    with pytest.raises(NotFoundError):
        testbed.start_checkout.run(
            StartCheckoutCommand(
                user_id=owner.id,
                business_id=business.id,
                request=StartCheckoutRequest(),
            )
        )


def test_a_provider_refusal_saves_no_payment_order() -> None:
    world = build_trial()
    world.testbed.flitt.refusal = {
        "response_status": "failure",
        "error_message": "Merchant is blocked",
    }

    with pytest.raises(ExternalServiceError):
        checkout(world)

    assert world.testbed.payment_order_repo.list_by_business(world.business.id) == []
    assert len(world.testbed.invoices(world.business.id)) == 2


def test_approved_payment_during_the_trial_pays_ahead_and_keeps_the_trial() -> None:
    world = build_trial()
    session = checkout(world)

    pay(world, session, payment_id=555)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    assert str(subscription.provider_reference) == str(session.payment_order_id)
    invoices = world.testbed.invoices(world.business.id)
    assert all(invoice.status is InvoiceStatus.PAID for invoice in invoices)
    assert {str(invoice.provider_reference) for invoice in invoices} == {"555"}
    assert payment_order(world, session).status is PaymentStatus.APPROVED
    assert world.testbed.notifier.sent == []


def test_repeated_notifications_change_nothing() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    parameters = world.testbed.callback_parameters(order, "approved", payment_id=7)
    first = world.testbed.deliver_flitt_callback(parameters)
    invoices_after_first = world.testbed.invoices(world.business.id)

    second = world.testbed.deliver_flitt_callback(parameters)

    assert first.outcome is PaymentWebhookOutcome.APPLIED
    assert second.outcome is PaymentWebhookOutcome.DUPLICATE
    assert second.payment_order_id == order.id
    assert world.testbed.invoices(world.business.id) == invoices_after_first
    assert payment_order(world, session).processed_notification_keys == ["7:approved"]


def test_trial_paid_ahead_becomes_active_when_it_ends() -> None:
    world, order = build_active_subscription()

    subscription = world.testbed.subscription(world.business.id)
    period_invoice = [
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    ][0]
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == period_invoice.period_start
    assert subscription.period_end == period_invoice.period_end
    assert subscription.grace_until is None
    assert str(subscription.provider_reference) == str(order.id)
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL


def test_payment_after_the_trial_activates_at_once() -> None:
    world = build_trial()
    world.testbed.clock.advance(days=20)
    session = checkout(world)

    pay(world, session)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == world.testbed.clock.now()
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL


def test_forged_or_unsigned_notifications_are_refused() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    parameters = world.testbed.callback_parameters(order, "approved")
    signed = sign_flitt_callback(parameters)

    for forged in (
        parameters,
        {**signed, "signature": "0" * 40},
        {**signed, "amount": 1},
        {**signed, "order_status": "declined"},
    ):
        with pytest.raises(AccessDeniedError):
            world.testbed.deliver_flitt_callback(forged, is_signed=False)

    assert all(
        invoice.status is InvoiceStatus.ISSUED
        for invoice in world.testbed.invoices(world.business.id)
    )
    assert payment_order(world, session).processed_notification_keys == []


def test_notifications_for_unknown_orders_are_not_found() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    stranger = order.model_copy(update={"id": PaymentOrderId()})

    with pytest.raises(NotFoundError):
        world.testbed.deliver_flitt_callback(
            {
                **world.testbed.callback_parameters(stranger, "approved"),
                "merchant_data": "not-ours",
            }
        )


def test_approved_amount_must_match_the_order() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    with pytest.raises(ValidationFailedError):
        world.testbed.deliver_flitt_callback(
            world.testbed.callback_parameters(order, "approved", amount=51700)
        )

    with pytest.raises(ValidationFailedError):
        world.testbed.deliver_flitt_callback(
            {
                **world.testbed.callback_parameters(order, "approved"),
                "currency": "EUR",
            }
        )

    assert payment_order(world, session).processed_notification_keys == []


def test_form_encoded_notifications_are_accepted() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved"),
        content_type="application/x-www-form-urlencoded",
        encoder=lambda parameters: urlencode(
            {key: str(value) for key, value in parameters.items()}
        ),
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def test_declined_first_payment_keeps_the_trial_and_tells_the_owner() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            order,
            "declined",
            response_description="Card expired",
        )
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    assert all(
        invoice.status is InvoiceStatus.FAILED
        for invoice in world.testbed.invoices(world.business.id)
    )
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.TRIALING
    )
    stored = payment_order(world, session)
    assert stored.status is PaymentStatus.DECLINED
    assert str(stored.last_failure_reason) == "Card expired"
    [(contact, text)] = world.testbed.notifier.sent
    assert contact.channel is ManagerContactChannel.WHATSAPP
    assert str(contact.address) == "+995599123456"
    assert str(contact.language) == "ka"
    assert "960,00\xa0₾" in str(text)

    retry = checkout(world)

    assert set(retry.invoice_ids) == set(session.invoice_ids)
    assert retry.payment_order_id != session.payment_order_id


def test_automatic_renewal_extends_the_subscription() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    world.testbed.clock.advance(hours=2)

    receipt = world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                "approved",
                payment_id=2,
                amount=51700,
            ),
            "order_id": f"{order.id}_2",
            "parent_order_id": str(order.id),
        }
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == period_end
    renewal = world.testbed.invoices(world.business.id)[-1]
    assert renewal.status is InvoiceStatus.PAID
    assert renewal.period_start == period_end
    assert str(renewal.provider_reference) == "2"


def test_declined_renewal_starts_the_grace_period() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)

    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "declined", payment_id=3, amount=51700)
    )

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    assert subscription.grace_until is not None
    assert int(subscription.grace_until) - int(world.testbed.clock.now()) == (
        7 * 24 * 60 * 60 * 1_000_000
    )
    failed = world.testbed.invoices(world.business.id)[-1]
    assert failed.status is InvoiceStatus.FAILED
    assert failed.period_start == period_end
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL
    [(_, text)] = world.testbed.notifier.sent
    assert "517,00\xa0₾" in str(text)
    assert "ამ თარიღამდე" in str(text)


def test_other_statuses_are_recorded_only() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    processing = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "processing")
    )
    expired = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "expired")
    )

    assert processing.outcome is PaymentWebhookOutcome.IGNORED
    assert expired.outcome is PaymentWebhookOutcome.IGNORED
    assert payment_order(world, session).status is PaymentStatus.EXPIRED
    assert all(
        invoice.status is InvoiceStatus.ISSUED
        for invoice in world.testbed.invoices(world.business.id)
    )
    assert world.testbed.notifier.sent == []


def test_reversal_is_recorded_for_the_admin() -> None:
    world = build_trial()
    session = checkout(world)
    pay(world, session)
    order = payment_order(world, session)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "reversed", payment_id=1)
    )
    late_processing = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "processing", payment_id=9)
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    assert late_processing.outcome is PaymentWebhookOutcome.IGNORED
    assert payment_order(world, session).status is PaymentStatus.REVERSED


def test_nothing_to_pay_while_automatic_payments_run() -> None:
    world, _ = build_active_subscription()

    with pytest.raises(ConflictError):
        checkout(world)


def test_plan_change_stops_automatic_charges_at_the_old_price() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end

    world.testbed.change_plan.run(
        ChangePlanCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=ChangePlanRequest(
                plan_key=PlanKey.PLUS,
                billing_period=BillingPeriod.MONTHLY,
            ),
        )
    )
    session = checkout(world)

    assert world.testbed.flitt.stopped_orders == [str(order.id)]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.provider_reference is None
    assert int(subscription.price_minor) == 103100
    next_invoice = world.testbed.invoices(world.business.id)[-1]
    assert next_invoice.period_start == period_end
    assert int(next_invoice.amount_minor) == 103100
    assert session.invoice_ids == [next_invoice.id]


def test_plan_change_voids_bills_at_the_old_price() -> None:
    world = build_trial()
    checkout(world)

    world.testbed.change_plan.run(
        ChangePlanCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=ChangePlanRequest(
                plan_key=PlanKey.VOICE_AND_CHAT,
                billing_period=BillingPeriod.ANNUAL,
            ),
        )
    )

    assert [
        invoice.status for invoice in world.testbed.invoices(world.business.id)
    ] == [InvoiceStatus.VOID, InvoiceStatus.VOID]
    session = checkout(world)
    [annual] = [
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.status is InvoiceStatus.ISSUED
    ]
    assert int(annual.amount_minor) == 527340
    assert session.invoice_ids == [annual.id]


def test_cancel_stops_automatic_charges() -> None:
    world, order = build_active_subscription()

    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )

    assert world.testbed.flitt.stopped_orders == [str(order.id)]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.CANCELLED
    assert subscription.provider_reference is None


def test_webhook_body_round_trips_as_json_text() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved"),
        encoder=lambda parameters: json.dumps({"response": parameters}),
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def test_late_retry_pays_the_bill_of_the_missed_renewal() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    world.testbed.clock.advance(days=2)
    world.testbed.run_job(world.testbed.enforce_grace_periods, "enforce_grace_periods")
    invoice_count = len(world.testbed.invoices(world.business.id))

    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved", payment_id=4, amount=51700)
    )

    invoices = world.testbed.invoices(world.business.id)
    assert len(invoices) == invoice_count
    assert invoices[-1].period_start == period_end
    assert invoices[-1].status is InvoiceStatus.PAID
    assert str(invoices[-1].provider_reference) == "4"
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == period_end
    assert subscription.grace_until is None


def test_a_renewal_is_billed_once_even_when_its_record_is_lost() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    declined = world.testbed.callback_parameters(
        order, "declined", payment_id=5, amount=51700
    )
    world.testbed.deliver_flitt_callback(declined)
    stored = world.testbed.payment_order_repo.get(order.id)
    assert stored is not None
    stored.processed_notification_keys.clear()
    world.testbed.payment_order_repo.save(stored)
    invoice_count = len(world.testbed.invoices(world.business.id))

    world.testbed.deliver_flitt_callback(declined)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved", payment_id=5, amount=51700)
    )

    invoices = world.testbed.invoices(world.business.id)
    assert len(invoices) == invoice_count
    assert invoices[-1].status is InvoiceStatus.PAID
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )


def test_cancel_voids_unpaid_bills() -> None:
    world = build_trial()
    checkout(world)

    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )

    assert {
        invoice.status for invoice in world.testbed.invoices(world.business.id)
    } == {InvoiceStatus.VOID}
    assert world.testbed.flitt.stopped_orders == []


def test_a_second_payment_for_paid_bills_keeps_them_paid() -> None:
    world = build_trial()
    first = checkout(world)
    second = checkout(world)
    pay(world, first, payment_id=1)

    pay(world, second, payment_id=2)

    invoices = world.testbed.invoices(world.business.id)
    assert {str(invoice.provider_reference) for invoice in invoices} == {"1"}
    assert str(world.testbed.subscription(world.business.id).provider_reference) == (
        str(second.payment_order_id)
    )


def test_a_decline_after_a_plan_change_leaves_voided_bills_alone() -> None:
    world = build_trial()
    session = checkout(world)
    world.testbed.change_plan.run(
        ChangePlanCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=ChangePlanRequest(
                plan_key=PlanKey.CHAT,
                billing_period=BillingPeriod.MONTHLY,
            ),
        )
    )

    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(payment_order(world, session), "declined")
    )

    statuses = [invoice.status for invoice in world.testbed.invoices(world.business.id)]
    assert statuses == [InvoiceStatus.FAILED, InvoiceStatus.VOID]


def test_payment_for_a_missing_subscription_is_not_found() -> None:
    world = build_trial()
    session = checkout(world)
    orphan = payment_order(world, session).model_copy(
        update={"id": PaymentOrderId(), "subscription_id": SubscriptionId()}
    )
    world.testbed.payment_order_repo.save(orphan)

    with pytest.raises(NotFoundError):
        world.testbed.deliver_flitt_callback(
            world.testbed.callback_parameters(orphan, "approved")
        )
