"""
Day 0 of a business: periods never start before it went live (or was
created), and its free trial costs nothing, so no return against the plan.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import BillingPeriod, SubscriptionStatus
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.setup import ActivationEventDocument
from app.schemas.dto.operations.dashboard import DashboardStatsQuery
from app.schemas.dto.value.value_model import ValueModel
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import EstimatedRevenueMinor
from app.use_cases.insights.value.compute_value_model_use_case import (
    ComputeValueModelUseCase,
)
from app.use_cases.insights.value.get_business_value_use_case import (
    GetBusinessValueUseCase,
)
from app.use_cases.insights.value.value_return import (
    PlanPrices,
    PlanTerms,
    plan_return,
)
from app.utilities.setup.setup_keys import derive_activation_event_id
from tests.value.test_value_estimates import value_query
from tests.value.test_value_return import SEPTEMBER, price, terms
from tests.value.value_scene import ValueScene, at

GEL: CurrencyCode = CurrencyCode("GEL")
# The scene's today: Monday 2026-10-05, 12:00 in Tbilisi.
LAUNCHED: str = "2026-10-05T10:40:00+04:00"


def opened_today(scene: ValueScene) -> None:
    """The business was created this morning and went live at 10:40."""

    scene.business.created_at = at("2026-10-05T09:15:00+04:00")
    scene.world.business_repo.save(scene.business)
    scene.world.activation_event_repo.record_once(
        ActivationEventDocument(
            id=derive_activation_event_id(
                scene.business.id, ActivationEventKind.WENT_LIVE
            ),
            business_id=scene.business.id,
            kind=ActivationEventKind.WENT_LIVE,
            occurred_at=at(LAUNCHED),
        )
    )


def trial(scene: ValueScene, status: SubscriptionStatus) -> None:
    scene.world.subscription_repo.save(
        SubscriptionDocument(
            business_id=scene.business.id,
            plan_key=scene.business.plan_key,
            billing_period=BillingPeriod.MONTHLY,
            price_minor=51_000,  # type: ignore[arg-type]
            currency_code=GEL,
            status=status,
            trial_ends_at=at("2026-10-19T10:40:00+04:00"),
            period_start=at("2026-10-05T10:40:00+04:00"),
            period_end=at("2026-11-05T10:40:00+04:00"),
        )
    )


def value_with_prices(scene: ValueScene) -> GetBusinessValueUseCase:
    world = scene.world
    return GetBusinessValueUseCase(
        authorize_business_access=world.authorize(),
        compute_value_model=ComputeValueModelUseCase(
            business_repo=world.business_repo,
            business_profile_repo=world.profile_repo,
            schedule_exception_repo=world.exception_repo,
            sources=world.value_sources(),
            catalogs=world.catalogs(),
            plan_prices=PlanPrices(
                subscription_repo=world.subscription_repo,
                plan_registry=world.plan_registry,
            ),
        ),
        activation_event_repo=world.activation_event_repo,
        wall_clock=world.clock.wall_clock,
    )


def test_a_business_launched_today_counts_from_today() -> None:
    scene = ValueScene()
    opened_today(scene)

    model = scene.world.business_value().run(value_query(scene))

    assert (model.date_from, model.date_to) == ("2026-10-05", "2026-10-05")
    assert (model.previous_date_from, model.previous_date_to) == (
        "2026-10-04",
        "2026-10-04",
    )
    assert model.is_since_launch is True
    assert model.went_live_at == at(LAUNCHED)


def test_a_business_created_inside_the_window_counts_from_its_creation() -> None:
    scene = ValueScene()
    scene.business.created_at = at("2026-09-20T18:00:00+04:00")
    scene.world.business_repo.save(scene.business)
    before = scene.conversation("2026-09-12T13:00:00+04:00")
    after = scene.conversation("2026-09-25T13:00:00+04:00")
    del before, after

    model = scene.world.business_value().run(value_query(scene))

    # Not live through the setup's milestones: its creation day is the floor.
    assert (model.date_from, model.date_to) == ("2026-09-20", "2026-10-05")
    assert model.previous_date_to == "2026-09-19"
    assert model.is_since_launch is True and model.went_live_at is None
    assert model.current.conversation_count == 1


def test_a_period_after_the_launch_is_kept_as_asked() -> None:
    scene = ValueScene()

    model = scene.world.business_value().run(
        value_query(scene, date_from="2026-09-10", date_to="2026-09-19")
    )

    assert (model.date_from, model.date_to) == ("2026-09-10", "2026-09-19")
    assert model.is_since_launch is False


def test_a_period_ending_before_the_business_keeps_only_its_last_day() -> None:
    scene = ValueScene()
    opened_today(scene)

    model = scene.world.business_value().run(
        value_query(scene, date_from="2026-09-01", date_to="2026-09-30")
    )

    assert (model.date_from, model.date_to) == ("2026-09-30", "2026-09-30")


def test_the_dashboard_counts_from_the_launch_too() -> None:
    scene = ValueScene()
    opened_today(scene)
    scene.conversation("2026-10-05T11:00:00+04:00")

    stats = scene.world.dashboard().run(
        DashboardStatsQuery(user_id=scene.owner.id, business_id=scene.business.id)
    )
    asked = scene.world.dashboard().run(
        DashboardStatsQuery(
            user_id=scene.owner.id,
            business_id=scene.business.id,
            date_from=LocalDate("2026-10-05"),
        )
    )

    assert (stats.date_from, stats.date_to, stats.is_since_launch) == (
        "2026-10-05",
        "2026-10-05",
        True,
    )
    assert [day.date for day in stats.daily] == ["2026-10-05"]
    assert stats.conversation_count == 1
    assert asked.is_since_launch is False


def test_the_trial_has_no_plan_cost_nor_multiple_only_the_price_after_it() -> None:
    scene = ValueScene()
    opened_today(scene)
    trial(scene, SubscriptionStatus.TRIALING)
    lunch = scene.conversation("2026-10-05T11:00:00+04:00")
    scene.booking("2026-10-05T11:05:00+04:00", lunch, value=(20_000, "GEL"))

    model: ValueModel = value_with_prices(scene).run(value_query(scene))
    staff: ValueModel = value_with_prices(scene).run(
        value_query(scene, user_id=scene.staff_id)
    )

    assert model.current.estimated_revenue_minor == 20_000
    assert (model.plan_cost_minor, model.return_multiple) == (None, None)
    assert model.is_trial is True
    assert model.trial_ends_at == at("2026-10-19T10:40:00+04:00")
    assert model.plan_cost_after_trial_minor == 51_000
    assert staff.is_trial is True and staff.plan_cost_after_trial_minor is None


def test_a_paying_business_gets_its_multiple_back_after_the_trial() -> None:
    scene = ValueScene()
    opened_today(scene)
    trial(scene, SubscriptionStatus.ACTIVE)
    lunch = scene.conversation("2026-10-05T11:00:00+04:00")
    scene.booking("2026-10-05T11:05:00+04:00", lunch, value=(20_000, "GEL"))

    model: ValueModel = value_with_prices(scene).run(value_query(scene))

    # One day of 510 GEL a month: 16.76 GEL.
    assert model.plan_cost_minor == 1_676
    assert model.return_multiple == 11.9
    assert (model.is_trial, model.plan_cost_after_trial_minor) == (False, None)


def test_no_multiple_for_an_estimate_of_nothing() -> None:
    nothing = plan_return(terms(29_300), GEL, *SEPTEMBER, EstimatedRevenueMinor(0))
    crumbs = plan_return(terms(29_300), GEL, *SEPTEMBER, EstimatedRevenueMinor(100))

    assert (nothing.plan_cost_minor, nothing.return_multiple) == (29_300, None)
    # 100 / 29 300 rounds to 0.0: no "≈ 0.0×".
    assert crumbs.return_multiple is None


def test_a_trial_in_another_currency_names_no_price() -> None:
    returned = plan_return(
        PlanTerms(
            monthly_price=price(7_900, "EUR"),
            is_trial=True,
            trial_ends_at=Microseconds(1),
        ),
        GEL,
        *SEPTEMBER,
        EstimatedRevenueMinor(50_000),
    )

    assert returned.is_trial is True
    assert returned.trial_ends_at == 1
    assert (returned.plan_cost_minor, returned.price_after_trial) == (None, None)
