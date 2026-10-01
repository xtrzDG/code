"""Subscribing with payment now: without a trial, after it, after cancelling."""

import pytest

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.client_health import ClientHealthIssue
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import AdminClientsQuery
from app.schemas.dto.billing_cabinet import (
    BillingOverviewQuery,
    CancelSubscriptionCommand,
    CheckoutSessionView,
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
    SubscribeCommand,
    SubscribeRequest,
)
from app.schemas.dto.payments import PaymentWebhookReceipt
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_strings import PaymentReturnUrl
from app.use_cases.billing.billing_records import is_service_paid_for
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.billing_testbed import (
    CABINET_ORIGIN,
    GEORGIA,
    BillingTestbed,
    bearer,
)


class World:
    def __init__(self) -> None:
        self.testbed = BillingTestbed()
        self.owner: UserDocument = self.testbed.add_user(phone_number="+995599123456")
        self.staff: UserDocument = self.testbed.add_user(email="staff@example.com")
        self.business: BusinessDocument = self.testbed.add_business(
            self.owner,
            GEORGIA,
            staff=[self.staff],
        )

    def subscribe(
        self,
        plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
        billing_period: BillingPeriod = BillingPeriod.MONTHLY,
        return_url: str | None = f"{CABINET_ORIGIN}/billing",
        user: UserDocument | None = None,
    ) -> CheckoutSessionView:
        return self.testbed.subscribe.execute(
            SubscribeCommand(
                user_id=(user or self.owner).id,
                business_id=self.business.id,
                request=SubscribeRequest(
                    plan_key=plan_key,
                    billing_period=billing_period,
                    return_url=None
                    if return_url is None
                    else PaymentReturnUrl(return_url),
                ),
            )
        )

    def start_trial(self) -> None:
        self.testbed.start_trial.run(
            StartTrialCommand(
                user_id=self.owner.id,
                business_id=self.business.id,
                request=StartTrialRequest(),
            )
        )

    def pay(self, session: CheckoutSessionView, payment_id: int = 1) -> None:
        order = self.testbed.payment_order_repo.get(session.payment_order_id)
        assert order is not None
        receipt: PaymentWebhookReceipt = self.testbed.deliver_flitt_callback(
            self.testbed.callback_parameters(order, "approved", payment_id=payment_id)
        )
        assert receipt.payment_order_id == session.payment_order_id

    def open_invoices(self) -> list[InvoiceKind]:
        return [
            invoice.kind
            for invoice in self.testbed.invoices(self.business.id)
            if invoice.status is InvoiceStatus.ISSUED
        ]


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


def test_subscribing_after_an_unpaid_trial_switches_plan_and_bills_from_now() -> None:
    world = World()
    world.start_trial()
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.PAST_DUE
    )

    session = world.subscribe(PlanKey.CHAT, BillingPeriod.ANNUAL)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.plan_key is PlanKey.CHAT
    assert subscription.billing_period is BillingPeriod.ANNUAL
    invoices = world.testbed.invoices(world.business.id)
    open_invoices = [
        invoice for invoice in invoices if invoice.status is InvoiceStatus.ISSUED
    ]
    assert [invoice.kind for invoice in open_invoices] == [InvoiceKind.SERVICE_PERIOD]
    assert open_invoices[0].period_start == world.testbed.clock.now()
    assert int(open_invoices[0].amount_minor) == int(subscription.price_minor)
    assert set(session.invoice_ids) == {open_invoices[0].id}
    world.pay(session)
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )


def test_subscribing_after_the_trial_on_the_same_plan_pays_the_open_bills() -> None:
    world = World()
    world.start_trial()
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    open_before = {
        invoice.id
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.status is InvoiceStatus.ISSUED
    }

    session = world.subscribe()

    assert set(session.invoice_ids) == open_before
    world.pay(session)
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )


def test_subscribing_after_cancelling_resumes_the_service() -> None:
    world = World()
    world.start_trial()
    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )
    world.testbed.clock.advance(days=20)

    world.pay(world.subscribe())

    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )


def test_subscribing_while_automatic_payments_run_has_nothing_to_pay() -> None:
    world = World()
    world.pay(world.subscribe())

    with pytest.raises(ConflictError):
        world.subscribe()

    assert world.testbed.flitt.stopped_orders == []


def test_a_foreign_return_page_is_refused_before_anything_changes() -> None:
    world = World()

    with pytest.raises(ValidationFailedError):
        world.subscribe(return_url="https://evil.example/billing")

    assert world.testbed.subscription_repo.list_by_business(world.business.id) == []
    assert world.testbed.flitt.checkout_orders == []


def test_staff_cannot_subscribe() -> None:
    world = World()

    with pytest.raises(AccessDeniedError):
        world.subscribe(user=world.staff)

    assert world.testbed.subscription_repo.list_by_business(world.business.id) == []


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


def test_subscribe_route_answers_with_the_payment_page() -> None:
    world = World()
    client = world.testbed.build_http_client()
    path = f"/v1/businesses/{world.business.id}/billing/subscribe"

    created = client.post(
        path,
        headers=bearer(world.owner),
        json={"plan_key": "plus", "billing_period": "annual"},
    )
    missing_plan = client.post(path, headers=bearer(world.owner), json={})
    staff = client.post(
        path,
        headers=bearer(world.staff),
        json={"plan_key": "plus"},
    )

    assert created.status_code == 201
    assert created.json()["checkout_url"]
    assert missing_plan.status_code == 422
    assert staff.status_code == 403


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
