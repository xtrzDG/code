"""Retries of a declined Flitt charge on days 1, 3 and 6 of the grace period."""

import threading

from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.payments import PaymentRetryOutcome, PaymentWebhookOutcome
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.billing.payment_retry_identity import derive_payment_retry_id
from tests.billing.paid_world import PaidWorld, build_active_subscription, build_trial
from tests.payments.payment_world import CARD_TOKEN, flitt_pay_with_card

DAY_HOURS: int = 24


def build_declined_charge(
    with_card: bool = True,
) -> tuple[PaidWorld, PaymentOrderDocument, InvoiceDocument]:
    """
    A Georgian business (its owner reads English) whose automatic charge
    at the end of its first paid month was declined.
    """

    if with_card:
        world = build_trial()
        order = flitt_pay_with_card(world)
        world.testbed.clock.advance(days=14, hours=1)
        world.testbed.run_job(world.testbed.end_trials, "end_trials")
    else:
        world, order = build_active_subscription()

    owner = world.testbed.user_repo.get(world.owner.id)
    assert owner is not None
    owner.locale = LanguageTag("en")
    world.testbed.user_repo.save(owner)
    world.testbed.clock.move_to(
        world.testbed.subscription(world.business.id).period_end
    )
    world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                "declined",
                payment_id=5,
                amount=int(order.recurring_amount_minor),
            ),
            "order_id": f"{order.id}_2",
            "parent_order_id": str(order.id),
        }
    )
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.PAST_DUE
    )
    world.testbed.notifier.sent.clear()
    return world, order, world.testbed.invoices(world.business.id)[-1]


def run_dunning(world: PaidWorld) -> int:
    return world.testbed.run_job(
        world.testbed.payments.retry_failed_payments, "retry_failed_payments"
    )


def retries(
    world: PaidWorld, invoice: InvoiceDocument
) -> list[PaymentRetryAttemptDocument]:
    return world.testbed.payment_retry_repo.list_for_invoice(
        world.business.id, invoice.id
    )


def test_nothing_is_retried_before_the_first_day() -> None:
    world, _, _ = build_declined_charge()
    world.testbed.clock.advance(hours=DAY_HOURS - 1)

    assert run_dunning(world) == 0

    assert world.testbed.flitt.recurring_orders == []


def test_the_first_retry_charges_the_saved_card_on_day_one() -> None:
    world, order, invoice = build_declined_charge()
    world.testbed.clock.advance(hours=DAY_HOURS)

    assert run_dunning(world) == 1

    [sent] = world.testbed.flitt.recurring_orders
    retry_id = derive_payment_retry_id(invoice.id, PaymentRetryAttempt(1))
    assert sent["rectoken"] == CARD_TOKEN
    assert sent["order_id"] == str(retry_id)
    assert sent["merchant_data"] == str(order.id)
    assert sent["amount"] == int(order.recurring_amount_minor)
    [retry] = retries(world, invoice)
    assert retry.outcome is PaymentRetryOutcome.APPROVED
    assert retry.due_at == world.testbed.clock.now()
    [text] = world.testbed.notifier.texts()
    assert text.startswith(
        "Funicular VR: the payment of GEL517.00 went through on a new try. "
        "Thank you, the assistant keeps working in full.\n\nhttp"
    )
    assert run_dunning(world) == 0


def test_the_retry_notice_settles_the_declined_invoice() -> None:
    world, order, invoice = build_declined_charge()
    world.testbed.clock.advance(hours=DAY_HOURS)
    run_dunning(world)
    [retry] = retries(world, invoice)

    receipt = world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                "approved",
                payment_id=6,
                amount=int(order.recurring_amount_minor),
            ),
            "order_id": str(retry.id),
        }
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    [settled] = [
        stored
        for stored in world.testbed.invoices(world.business.id)
        if stored.id == invoice.id
    ]
    assert settled.status is InvoiceStatus.PAID
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.grace_until is None


def test_declined_retries_run_on_days_three_and_six_then_stop() -> None:
    world, _, invoice = build_declined_charge()
    world.testbed.flitt.recurring_status = "declined"
    outcomes: list[int] = []
    for _ in range(7):
        world.testbed.clock.advance(hours=DAY_HOURS)
        outcomes.append(run_dunning(world))

    assert outcomes[:6] == [1, 0, 1, 0, 0, 1]
    assert [int(retry.attempt) for retry in retries(world, invoice)] == [1, 2, 3]
    assert {retry.outcome for retry in retries(world, invoice)} == {
        PaymentRetryOutcome.DECLINED
    }
    texts = world.testbed.notifier.texts()
    assert len(texts) == 3
    assert texts[0].startswith(
        "Funicular VR: we tried to charge GEL517.00 again and the card was "
        "declined. The next try is on "
    )
    assert "You can pay or update the card in Billing." in texts[0]
    assert "The assistant keeps full service until" in texts[0]
    assert texts[2].startswith(
        "Funicular VR: the last try to charge GEL517.00 was declined."
    )
    assert len(world.testbed.flitt.recurring_orders) == 3


def test_a_retry_missed_while_the_job_did_not_run_is_skipped() -> None:
    world, _, invoice = build_declined_charge()
    world.testbed.flitt.recurring_status = "declined"
    world.testbed.clock.advance(hours=3 * DAY_HOURS + 1)

    assert run_dunning(world) == 1

    assert [
        (int(retry.attempt), retry.outcome) for retry in retries(world, invoice)
    ] == [(1, PaymentRetryOutcome.SKIPPED), (2, PaymentRetryOutcome.DECLINED)]
    assert len(world.testbed.flitt.recurring_orders) == 1


def test_two_workers_charge_a_retry_once() -> None:
    world, _, invoice = build_declined_charge()
    world.testbed.clock.advance(hours=DAY_HOURS)
    repo = world.testbed.payment_retry_repo
    claim = repo.claim
    both_claiming = threading.Barrier(2, timeout=10)

    def claim_together(attempt: PaymentRetryAttemptDocument) -> bool:
        both_claiming.wait()
        return claim(attempt)

    repo.claim = claim_together  # type: ignore[method-assign]
    counts: list[int] = []
    workers = [
        threading.Thread(target=lambda: counts.append(run_dunning(world)))
        for _ in range(2)
    ]
    for worker in workers:
        worker.start()

    for worker in workers:
        worker.join(timeout=30)

    assert sorted(counts) == [0, 1]
    assert len(world.testbed.flitt.recurring_orders) == 1
    assert len(retries(world, invoice)) == 1


def test_a_charge_without_a_saved_card_cannot_be_retried() -> None:
    world, _, invoice = build_declined_charge(with_card=False)
    world.testbed.clock.advance(hours=DAY_HOURS)

    assert run_dunning(world) == 1

    [retry] = retries(world, invoice)
    assert retry.outcome is PaymentRetryOutcome.NOT_POSSIBLE
    assert world.testbed.flitt.recurring_orders == []
    assert world.testbed.notifier.sent == []


def test_a_retry_that_does_not_reach_flitt_is_recorded_as_failed() -> None:
    world, _, invoice = build_declined_charge()
    world.testbed.flitt.http_status = 503
    world.testbed.clock.advance(hours=DAY_HOURS)

    assert run_dunning(world) == 1

    [retry] = retries(world, invoice)
    assert retry.outcome is PaymentRetryOutcome.FAILED
    assert world.testbed.notifier.sent == []


def test_the_retry_notices_reach_the_owners_telegram_chats() -> None:
    world, _, _ = build_declined_charge()
    business = world.testbed.business(world.business.id)
    business.manager_contacts.append(
        ManagerContact(
            name=ManagerName("Nino"),
            channel=ManagerContactChannel.TELEGRAM,
            address=ManagerContactAddress("700000001"),
            language=LanguageTag("it"),
        )
    )
    world.testbed.business_repo.save(business)
    world.testbed.flitt.recurring_status = "declined"
    world.testbed.clock.advance(hours=DAY_HOURS)

    run_dunning(world)

    channels = [contact.channel for contact, _ in world.testbed.notifier.sent]
    assert sorted(channel.value for channel in channels) == sorted(
        [ManagerContactChannel.TELEGRAM.value, ManagerContactChannel.WHATSAPP.value]
    )
    [(_, italian)] = [
        (contact, text)
        for contact, text in world.testbed.notifier.sent
        if contact.channel is ManagerContactChannel.TELEGRAM
    ]
    assert str(italian).startswith(
        "Funicular VR: abbiamo provato di nuovo ad addebitare 517,00\xa0GEL e la "
        "carta è stata rifiutata."
    )


def test_no_retry_runs_once_the_grace_period_is_over() -> None:
    world, _, invoice = build_declined_charge()
    world.testbed.clock.advance(hours=8 * DAY_HOURS)

    assert run_dunning(world) == 0

    assert retries(world, invoice) == []


def test_a_trial_never_has_retries() -> None:
    world = build_trial()

    assert run_dunning(world) == 0
