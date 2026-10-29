"""
Metrics that count every business (R13): the business-level funnel and
tunnel of the businesses created in the period, a second business of an
owner who signed up long before included; owners who are platform admins
left out with a visible count unless the founder includes them; and the
rates MRR was converted with.
"""

from app.schemas.constants.analytics import FunnelStep, ProductEventName, TunnelStepKey
from app.schemas.domain.product_events import ProductEventProperties
from app.schemas.dto.analytics.admin_metrics_view import AdminMetricsView
from app.schemas.dto.analytics.growth_views import BusinessGrowthView
from app.schemas.typings.analytics.constrained_strings import MetricsDate
from tests.analytics.metric_events import GEL, billing, event, tunnel
from tests.analytics.metrics_world import MetricsWorld

N = ProductEventName
OCTOBER = {
    "period_start": MetricsDate("2026-10-01"),
    "period_end": MetricsDate("2026-10-14"),
}


def businesses_of(metrics: AdminMetricsView) -> BusinessGrowthView:
    assert metrics.growth.businesses is not None
    return metrics.growth.businesses


def funnel_counts(metrics: AdminMetricsView) -> dict[FunnelStep, int]:
    return {step.step: int(step.businesses) for step in businesses_of(metrics).funnel}


def test_a_second_business_of_an_existing_owner_appears_in_the_business_funnel() -> (
    None
):
    world = MetricsWorld(today=44)
    nino = world.add_user(1)
    world.add_business(nino, 1)
    second = world.add_business(nino, 32).id
    world.record(
        event(N.BUSINESS_CREATED, 32, second, nino.id),
        event(N.WENT_LIVE, 33, second),
        event(N.CHANNEL_CONNECTED, 33.5, second),
    )

    metrics = world.metrics(**OCTOBER)

    growth = businesses_of(metrics)
    assert int(growth.created) == 1
    assert int(growth.by_returning_owners) == 1
    assert funnel_counts(metrics) == {
        FunnelStep.BUSINESS_CREATED: 1,
        FunnelStep.LAUNCH_ATTEMPTED: 1,
        FunnelStep.WENT_LIVE: 1,
        FunnelStep.CHANNEL_CONNECTED: 1,
        FunnelStep.FIRST_CONVERSATION: 0,
        FunnelStep.PAID: 0,
    }
    assert growth.funnel[1].share_of_created is not None
    assert float(growth.funnel[1].share_of_created) == 100.0
    # The owners' funnel counts the period's sign-ups: Nino signed up in
    # September, so it stays empty.
    assert int(metrics.growth.funnel[0].owners) == 0


def test_platform_admin_owners_are_left_out_and_counted_unless_included() -> None:
    world = MetricsWorld(today=44)
    founder = world.add_user(31, is_platform_admin=True)
    cafe = world.add_business(founder, 31).id
    world.record(event(N.WENT_LIVE, 31.5, cafe))
    owner = world.add_user(32)
    world.add_business(owner, 32)

    left_out = world.metrics(**OCTOBER)
    included = world.metrics(**OCTOBER, include_platform_admins=True)

    assert int(left_out.growth.excluded_platform_admins) == 1
    assert int(left_out.growth.excluded_admin_businesses) == 1
    assert left_out.growth.are_platform_admins_included is False
    assert int(left_out.growth.funnel[0].owners) == 1
    assert int(businesses_of(left_out).created) == 1
    assert int(included.growth.excluded_platform_admins) == 0
    assert int(included.growth.excluded_admin_businesses) == 0
    assert included.growth.are_platform_admins_included is True
    assert int(included.growth.funnel[0].owners) == 2
    assert int(businesses_of(included).created) == 2
    assert funnel_counts(included)[FunnelStep.WENT_LIVE] == 1


def test_the_business_tunnel_gives_the_first_screens_to_the_business_made_next() -> (
    None
):
    world = MetricsWorld(today=44)
    nino = world.add_user(1)
    world.add_business(nino, 1)
    second = world.add_business(nino, 33).id
    world.record(
        tunnel(N.TUNNEL_STEP_ENTERED, 32.9, nino.id, TunnelStepKey.BUSINESS),
        tunnel(N.TUNNEL_STEP_COMPLETED, 32.95, nino.id, TunnelStepKey.BUSINESS),
        event(
            N.TUNNEL_STEP_ENTERED,
            33.1,
            second,
            nino.id,
            properties=ProductEventProperties(tunnel_step=TunnelStepKey.OFFER),
        ),
        # A third setup after the second business, still on its way.
        tunnel(N.TUNNEL_STEP_ENTERED, 40, nino.id, TunnelStepKey.BUSINESS),
    )

    growth = businesses_of(world.metrics(**OCTOBER))

    steps = {step.step: step for step in growth.tunnel}
    assert int(steps[TunnelStepKey.BUSINESS].entered) == 2
    assert int(steps[TunnelStepKey.BUSINESS].completed) == 1
    assert int(steps[TunnelStepKey.BUSINESS].stopped_here) == 1
    assert int(steps[TunnelStepKey.OFFER].entered) == 1
    assert int(steps[TunnelStepKey.OFFER].stopped_here) == 1


def test_mrr_names_the_rates_it_converted_with() -> None:
    world = MetricsWorld(today=44)
    owner = world.add_user(1)
    paying = world.add_business(owner, 1).id
    world.record(billing(N.SUBSCRIBED, 10, paying, 51700, GEL))

    mrr = world.metrics(**OCTOBER).revenue.mrr

    assert [
        (str(rate.base_currency_code), str(rate.quote_currency_code))
        for rate in mrr.rates
    ] == [("GEL", "EUR")]
    assert int(mrr.end.amount_minor) == 25850
