"""
The founder's growth metrics on in-memory repositories: the funnel of
owners (not invited staff, not admins), median time to go live, activation
within a week, trial to paid, the tunnel, cohorts, sources and filters.
"""

import pytest

from app.schemas.constants.analytics import (
    FunnelStep,
    ProductEventName,
    TunnelStepKey,
)
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.product_events import ProductEventProperties
from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.dto.analytics.admin_metrics_query import AdminMetricsQuery
from app.schemas.dto.analytics.admin_metrics_view import AdminMetricsView
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.analytics.constrained_strings import (
    AcquisitionSourceKey,
    MetricsDate,
    ReferralCode,
    UtmSource,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from tests.analytics.metric_events import DAY, at_day, billing, event, tunnel
from tests.analytics.metrics_world import MetricsWorld

N = ProductEventName


def build_world() -> MetricsWorld:
    """
    September: Ana (Facebook) goes live in two days, activates and pays
    after her trial; Boris (a referral) goes live after ten days and lets
    his trial end; Carla (Italy, no attribution) stops in the tunnel; Dima
    is Ana's staff. October: Eve went live yesterday (activation pending).
    """

    world = MetricsWorld(today=44)
    ana = world.add_user(1, SignupAttribution(utm_source=UtmSource("Facebook")))
    boris = world.add_user(2, SignupAttribution(referral_code=ReferralCode("p-7")))
    carla = world.add_user(3, country="IT")
    dima = world.add_user(4)
    eve = world.add_user(40)
    anas = world.add_business(ana, 1, staff=[dima]).id
    boriss = world.add_business(boris, 2, niche=NicheKey.BEAUTY_SALON).id
    eves = world.add_business(eve, 40).id
    trial_end = ProductEventProperties(trial_ends_at=at_day(17))
    world.record(
        event(N.BUSINESS_CREATED, 1, anas, ana.id),
        event(N.LAUNCH_BLOCKED, 2, anas),
        event(N.WENT_LIVE, 3, anas),
        event(N.TRIAL_STARTED, 3, anas, properties=trial_end),
        event(N.CHANNEL_CONNECTED, 4, anas),
        event(N.FIRST_REAL_CONVERSATION, 5, anas),
        billing(N.SUBSCRIBED, 17, anas, 4900),
        tunnel(N.TUNNEL_STEP_ENTERED, 1, ana.id, TunnelStepKey.BUSINESS),
        tunnel(N.TUNNEL_STEP_COMPLETED, 1, ana.id, TunnelStepKey.BUSINESS),
        tunnel(N.TUNNEL_STEP_SKIPPED, 2, ana.id, TunnelStepKey.CHANNELS),
        event(N.BUSINESS_CREATED, 2, boriss, boris.id),
        event(N.CHANNEL_CONNECTED, 3, boriss),
        event(N.WENT_LIVE, 12, boriss),
        event(
            N.TRIAL_STARTED,
            12,
            boriss,
            properties=ProductEventProperties(trial_ends_at=at_day(26)),
        ),
        event(N.FIRST_REAL_CONVERSATION, 13, boriss),
        tunnel(N.TUNNEL_STEP_ENTERED, 3, carla.id, TunnelStepKey.BUSINESS),
        tunnel(N.TUNNEL_STEP_ENTERED, 3, carla.id, TunnelStepKey.PLACE),
        event(N.SIGNED_IN, 4, user_id=dima.id),
        event(N.BUSINESS_CREATED, 40, eves, eve.id),
        event(N.WENT_LIVE, 41, eves),
    )
    return world


def funnel(view: AdminMetricsView) -> dict[FunnelStep, int]:
    return {step.step: int(step.owners) for step in view.growth.funnel}


def test_the_funnel_counts_owners_who_reached_every_step_before() -> None:
    view = build_world().metrics()

    assert funnel(view) == {
        FunnelStep.SIGNED_UP: 4,
        FunnelStep.BUSINESS_CREATED: 3,
        FunnelStep.LAUNCH_ATTEMPTED: 3,
        FunnelStep.WENT_LIVE: 3,
        FunnelStep.CHANNEL_CONNECTED: 2,
        FunnelStep.FIRST_CONVERSATION: 2,
        FunnelStep.PAID: 1,
    }
    paid = view.growth.funnel[-1]
    assert paid.share_of_sign_ups == 25.0
    assert paid.share_of_previous == 50.0
    # Ana two days, Boris ten, Eve one: the median is two days.
    assert view.growth.median_time_to_live_seconds == 2 * DAY // 1_000_000


def test_activation_and_trials_of_the_period() -> None:
    growth = build_world().metrics().growth

    assert (
        int(growth.activation.eligible),
        int(growth.activation.activated),
        int(growth.activation.pending),
        growth.activation.rate,
    ) == (2, 1, 1, 50.0)
    assert (
        int(growth.trials.started),
        int(growth.trials.ended),
        int(growth.trials.converted),
        growth.trials.rate,
    ) == (2, 2, 1, 50.0)


def test_the_tunnel_shows_where_owners_stopped() -> None:
    steps = {step.step: step for step in build_world().metrics().growth.tunnel}

    business = steps[TunnelStepKey.BUSINESS]
    assert (int(business.entered), int(business.completed)) == (2, 1)
    assert int(steps[TunnelStepKey.CHANNELS].skipped) == 1
    assert int(steps[TunnelStepKey.PLACE].stopped_here) == 1
    assert sum(int(step.stopped_here) for step in steps.values()) == 1


def test_cohorts_by_sign_up_month_and_sources() -> None:
    growth = build_world().metrics().growth

    cohorts = [
        (str(row.month), int(row.sign_ups), int(row.went_live), row.paying)
        for row in growth.cohorts
    ]
    assert cohorts == [
        ("2026-09", 3, 2, [33.33, 33.33]),
        ("2026-10", 1, 1, [0.0]),
    ]
    sources = [
        (str(row.source), int(row.sign_ups), int(row.went_live), int(row.paying))
        for row in growth.sources
    ]
    assert sources == [
        ("unknown", 2, 1, 0),
        ("facebook", 1, 1, 1),
        ("referral", 1, 1, 0),
    ]


def test_filters_keep_owners_of_one_source_country_or_niche() -> None:
    world = build_world()

    facebook = world.metrics(source=AcquisitionSourceKey("facebook"))
    assert funnel(facebook)[FunnelStep.SIGNED_UP] == 1
    assert int(facebook.growth.trials.converted) == 1

    italy = world.metrics(country_code=CountryCode("IT"))
    assert funnel(italy)[FunnelStep.SIGNED_UP] == 1
    assert funnel(italy)[FunnelStep.BUSINESS_CREATED] == 0

    salons = world.metrics(niche_key=NicheKey.BEAUTY_SALON)
    assert funnel(salons)[FunnelStep.SIGNED_UP] == 1
    assert int(salons.growth.activation.eligible) == 1
    assert int(salons.growth.activation.activated) == 0

    choices = world.metrics().choices
    assert [str(code) for code in choices.countries] == ["GE", "IT"]
    assert set(choices.niches) == {NicheKey.RESTAURANT, NicheKey.BEAUTY_SALON}
    assert [str(source) for source in choices.sources] == [
        "facebook",
        "referral",
        "unknown",
    ]


def test_the_period_bounds_the_sign_ups() -> None:
    october = build_world().metrics(period_start=MetricsDate("2026-10-01"))

    assert str(october.period_start) == "2026-10-01"
    assert str(october.period_end) == "2026-10-15"
    assert funnel(october)[FunnelStep.SIGNED_UP] == 1
    assert int(october.growth.activation.pending) == 1


def test_only_platform_admins_read_the_metrics() -> None:
    world = build_world()
    owner = world.add_user(5)

    with pytest.raises(AccessDeniedError):
        world.use_case.run(AdminMetricsQuery(user_id=owner.id))
