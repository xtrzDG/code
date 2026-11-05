"""
Revenue in the founder's metrics on in-memory repositories: MRR and its
movements in euros (a lari subscription at the official rate), ARPA, gross
margin from the client cost reports, and the cabinet's Web Vitals.
"""

from app.schemas.constants.analytics import (
    DeviceClass,
    MrrMovementKind,
    ProductEventName,
    WebVitalName,
    WebVitalRating,
)
from app.schemas.domain.web_vitals import WebVitalSampleDocument
from app.schemas.dto.billing import Money
from app.schemas.typings.analytics.constrained_integers import WebVitalValue
from app.schemas.typings.analytics.constrained_strings import (
    CabinetRoutePattern,
    MetricsDate,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from tests.analytics.metric_events import GEL, at_day, billing
from tests.analytics.metrics_world import MetricsWorld

N = ProductEventName
INBOX = CabinetRoutePattern("/b/[businessId]/inbox")


def money(amount: int, currency: str) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount), currency_code=CurrencyCode(currency)
    )


def revenue_world() -> MetricsWorld:
    """A lari restaurant paying since day 5; a euro salon from day 20 that
    upgrades on day 30; a third business that left on day 8."""

    world = MetricsWorld(today=44)
    owner = world.add_user(1)
    lari = world.add_business(owner, 1).id
    euro = world.add_business(owner, 2).id
    gone = world.add_business(owner, 3).id
    world.record(
        billing(N.SUBSCRIBED, 5, lari, 20000, GEL),
        billing(N.SUBSCRIBED, 6, gone, 2900),
        billing(N.CANCELLED, 8, gone),
        billing(N.SUBSCRIBED, 20, euro, 4900),
        billing(N.PLAN_CHANGED, 30, euro, 7900),
    )
    # 200 GEL and 2.50 USD; 79 EUR and 1.25 USD; nothing for the third.
    world.costs.reports[lari] = (money(20000, "GEL"), 2_500_000)
    world.costs.reports[euro] = (money(7900, "EUR"), 1_250_000)
    return world


def test_mrr_moves_from_the_start_to_the_end_of_the_period_in_euros() -> None:
    mrr = revenue_world().metrics(period_start=MetricsDate("2026-09-15")).revenue.mrr

    assert (int(mrr.start.amount_minor), str(mrr.start.currency_code)) == (
        10000,
        "EUR",
    )
    assert int(mrr.end.amount_minor) == 10000 + 7900
    assert int(mrr.net_change) == 7900
    moved = {
        movement.kind: (int(movement.amount.amount_minor), int(movement.accounts))
        for movement in mrr.movements
    }
    assert moved == {
        MrrMovementKind.NEW: (4900, 1),
        MrrMovementKind.REACTIVATION: (0, 0),
        MrrMovementKind.EXPANSION: (3000, 1),
        MrrMovementKind.CONTRACTION: (0, 0),
        MrrMovementKind.CHURN: (0, 0),
    }
    assert int(mrr.paying_accounts) == 2
    assert mrr.arpa is not None
    assert int(mrr.arpa.amount_minor) == (17900 + 1) // 2
    assert mrr.unconverted_currencies == []


def test_from_the_first_payment_on_every_movement_counts() -> None:
    whole = revenue_world().metrics(period_start=MetricsDate("2026-09-01")).revenue

    moved = {movement.kind: movement for movement in whole.mrr.movements}
    assert int(moved[MrrMovementKind.CHURN].amount.amount_minor) == 2900
    assert int(moved[MrrMovementKind.NEW].accounts) == 3
    assert int(whole.mrr.start.amount_minor) == 0


def test_gross_margin_sums_the_client_cost_reports_in_euros() -> None:
    margin = revenue_world().metrics().revenue.margin

    # 200 GEL = 100.00 EUR, 2.50 USD = 2.00 EUR; 79.00 EUR and 1.25 USD = 1 EUR.
    assert int(margin.revenue.amount_minor) == 10000 + 7900
    assert int(margin.provider_cost.amount_minor) == 200 + 100
    assert margin.gross_margin_percent == 98.32
    assert (int(margin.accounts), int(margin.accounts_without_rate)) == (2, 0)


def test_a_client_whose_revenue_has_no_rate_is_counted_apart() -> None:
    world = revenue_world()
    owner = world.add_user(2)
    drams = world.add_business(owner, 3).id
    world.costs.reports[drams] = (money(5000, "AMD"), 0)

    margin = world.metrics().revenue.margin

    assert (int(margin.accounts), int(margin.accounts_without_rate)) == (2, 1)


def add_vitals(world: MetricsWorld, day: float, values: list[int]) -> None:
    moment = at_day(day)
    world.vitals.add_many(
        [
            WebVitalSampleDocument(
                user_id=world.admin.id,
                metric=WebVitalName.LCP,
                value=WebVitalValue(value),
                route=INBOX,
                device_class=DeviceClass.MOBILE,
                created_at=moment,
                updated_at=moment,
            )
            for value in values
        ]
    )


def test_web_vitals_show_the_75th_percentile_of_the_period() -> None:
    world = MetricsWorld(today=44)
    add_vitals(world, 40, [1000, 1200, 3000, 5000])
    add_vitals(world, -60, [30000, 30000, 30000])

    (row,) = world.metrics().web_vitals

    assert (row.metric, str(row.route), row.device_class) == (
        WebVitalName.LCP,
        "/b/[businessId]/inbox",
        DeviceClass.MOBILE,
    )
    assert int(row.samples) == 4
    # The third of four samples ends the 3000-3500 bucket.
    assert int(row.p75) == 3500
    assert row.rating is WebVitalRating.NEEDS_IMPROVEMENT
