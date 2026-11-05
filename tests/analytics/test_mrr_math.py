"""
MRR from the billing steps: new, expansion (upgrade), contraction
(downgrade), churn and reactivation; start plus the movements is the end;
other currencies in euros, one without a rate left out and named.
"""

from app.schemas.constants.analytics import MrrMovementKind, ProductEventName
from app.schemas.dto.analytics.revenue_views import MrrView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.analytics.mrr_math import (
    RevenueState,
    apply_step,
    build_mrr,
    paying_businesses_at,
)
from tests.analytics.metric_events import (
    GEL,
    at_day,
    billing,
    euro_cents_at_two_gel_per_euro,
)

SUBSCRIBED = ProductEventName.SUBSCRIBED
PLAN_CHANGED = ProductEventName.PLAN_CHANGED
CANCELLED = ProductEventName.CANCELLED


def movements(view: MrrView) -> dict[MrrMovementKind, tuple[int, int]]:
    return {
        movement.kind: (int(movement.amount.amount_minor), int(movement.accounts))
        for movement in view.movements
    }


def signed_total(view: MrrView) -> int:
    amounts = {kind: amount for kind, (amount, _) in movements(view).items()}
    return (
        amounts[MrrMovementKind.NEW]
        + amounts[MrrMovementKind.REACTIVATION]
        + amounts[MrrMovementKind.EXPANSION]
        - amounts[MrrMovementKind.CONTRACTION]
        - amounts[MrrMovementKind.CHURN]
    )


def test_a_replayed_business_moves_through_every_kind() -> None:
    state = RevenueState()

    assert apply_step(state, SUBSCRIBED, 4900) == [(MrrMovementKind.NEW, 4900)]
    assert apply_step(state, PLAN_CHANGED, 7900) == [(MrrMovementKind.EXPANSION, 3000)]
    assert apply_step(state, PLAN_CHANGED, 2900) == [
        (MrrMovementKind.CONTRACTION, 5000)
    ]
    assert apply_step(state, CANCELLED, 0) == [(MrrMovementKind.CHURN, 2900)]
    assert apply_step(state, CANCELLED, 0) == []
    assert apply_step(state, SUBSCRIBED, 4900) == [(MrrMovementKind.REACTIVATION, 4900)]


def test_a_plan_change_of_a_business_that_does_not_pay_moves_nothing() -> None:
    state = RevenueState()

    assert apply_step(state, PLAN_CHANGED, 7900) == []
    assert apply_step(state, SUBSCRIBED, 7900) == [(MrrMovementKind.NEW, 7900)]
    assert apply_step(state, SUBSCRIBED, 7900) == []


def test_movements_of_the_period_lead_from_its_start_to_its_end() -> None:
    upgrading, downgrading, churning, newcomer, returning = (
        BusinessId() for _ in range(5)
    )
    events = [
        # Paying before the period (MRR at its start: 49 + 79 + 29 + 29).
        billing(SUBSCRIBED, 1, upgrading, 4900),
        billing(SUBSCRIBED, 2, downgrading, 7900),
        billing(SUBSCRIBED, 3, churning, 2900),
        billing(SUBSCRIBED, 4, returning, 2900),
        billing(CANCELLED, 5, returning),
        # The period: days 10 to 20.
        billing(PLAN_CHANGED, 11, upgrading, 7900),
        billing(PLAN_CHANGED, 12, downgrading, 4900),
        billing(CANCELLED, 13, churning),
        billing(SUBSCRIBED, 14, newcomer, 14900),
        billing(SUBSCRIBED, 15, returning, 4900),
        # After the period: not counted.
        billing(CANCELLED, 25, newcomer),
    ]

    view = build_mrr(
        events,
        {upgrading, downgrading, churning, newcomer, returning},
        at_day(10),
        at_day(20),
        euro_cents_at_two_gel_per_euro,
    )

    assert int(view.start.amount_minor) == 4900 + 7900 + 2900
    assert int(view.end.amount_minor) == 7900 + 4900 + 14900 + 4900
    assert str(view.end.currency_code) == "EUR"
    assert movements(view) == {
        MrrMovementKind.NEW: (14900, 1),
        MrrMovementKind.REACTIVATION: (4900, 1),
        MrrMovementKind.EXPANSION: (3000, 1),
        MrrMovementKind.CONTRACTION: (3000, 1),
        MrrMovementKind.CHURN: (2900, 1),
    }
    assert int(view.start.amount_minor) + signed_total(view) == int(
        view.end.amount_minor
    )
    assert int(view.net_change) == int(view.end.amount_minor) - int(
        view.start.amount_minor
    )
    assert int(view.paying_accounts) == 4
    assert view.arpa is not None
    assert int(view.arpa.amount_minor) == (7900 + 4900 + 14900 + 4900) // 4


def test_other_currencies_count_in_euros_and_one_without_a_rate_is_named() -> None:
    lari, unknown, euro = BusinessId(), BusinessId(), BusinessId()
    events = [
        billing(SUBSCRIBED, 1, lari, 20000, GEL),
        billing(SUBSCRIBED, 1, unknown, 9900, CurrencyCode("XYZ")),
        billing(SUBSCRIBED, 2, euro, 4900),
    ]

    view = build_mrr(
        events,
        {lari, unknown, euro},
        at_day(0),
        at_day(30),
        euro_cents_at_two_gel_per_euro,
    )

    assert int(view.end.amount_minor) == 10000 + 4900
    assert [str(code) for code in view.unconverted_currencies] == ["XYZ"]
    assert int(view.paying_accounts) == 2


def test_businesses_out_of_scope_are_left_out() -> None:
    kept, filtered_out = BusinessId(), BusinessId()
    events = [
        billing(SUBSCRIBED, 1, kept, 4900),
        billing(SUBSCRIBED, 1, filtered_out, 7900),
    ]

    view = build_mrr(
        events, {kept}, at_day(0), at_day(30), euro_cents_at_two_gel_per_euro
    )

    assert int(view.end.amount_minor) == 4900
    assert movements(view)[MrrMovementKind.NEW] == (4900, 1)


def test_no_paying_business_has_no_arpa() -> None:
    view = build_mrr([], set(), at_day(0), at_day(30), euro_cents_at_two_gel_per_euro)

    assert int(view.end.amount_minor) == 0
    assert view.arpa is None
    assert int(view.paying_accounts) == 0


def test_paying_businesses_at_a_moment() -> None:
    stays, leaves = BusinessId(), BusinessId()
    events = [
        billing(SUBSCRIBED, 1, stays, 4900),
        billing(SUBSCRIBED, 2, leaves, 4900),
        billing(CANCELLED, 10, leaves),
    ]

    assert paying_businesses_at(events, at_day(5)) == {stays, leaves}
    assert paying_businesses_at(events, at_day(11)) == {stays}
    assert paying_businesses_at(events, at_day(0)) == set()
