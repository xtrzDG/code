"""What the assistant returned against the plan's price (≈ N× the plan)."""

from datetime import date

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.billing.plan_registry import PlanRegistry
from app.repositories.billing_repositories import SubscriptionRepository
from app.schemas.constants.billing import BillingPeriod, SubscriptionStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.value.value_model import ValueModelQuery
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import EstimatedRevenueMinor
from app.use_cases.insights.value.compute_value_model_use_case import (
    ComputeValueModelUseCase,
)
from app.use_cases.insights.value.value_access import without_money
from app.use_cases.insights.value.value_return import (
    NO_RETURN,
    PlanPrices,
    monthly_plan_price,
    plan_return,
)
from tests.value.value_scene import ValueScene, at

SEPTEMBER = (date(2026, 9, 1), date(2026, 9, 30))
GEL: CurrencyCode = CurrencyCode("GEL")


def price(amount: int, currency: str = "GEL") -> Money:
    return Money.model_validate({"amount_minor": amount, "currency_code": currency})


def estimate(amount: int) -> EstimatedRevenueMinor:
    return EstimatedRevenueMinor(amount)


def prices() -> PlanPrices:
    return PlanPrices(
        subscription_repo=SubscriptionRepository(
            InMemoryDocumentCollectionAdapter[SubscriptionDocument](
                SubscriptionDocument
            )
        ),
        plan_registry=PlanRegistry(),
    )


def test_a_calendar_month_against_the_whole_monthly_price() -> None:
    returned = plan_return(price(29_300), GEL, *SEPTEMBER, estimate(109_000))

    assert returned.plan_cost_minor == 29_300
    # 109 000 / 29 300 = 3.72: one decimal, half up.
    assert returned.return_multiple == 3.7


def test_a_week_against_its_share_of_the_month() -> None:
    returned = plan_return(
        price(29_300), GEL, date(2026, 9, 28), date(2026, 10, 4), estimate(20_000)
    )

    # 29 300 x 7 / 30.436875 days = 6 738.6.
    assert returned.plan_cost_minor == 6_739
    assert returned.return_multiple == 3.0


def test_no_multiple_when_the_currencies_differ_or_nothing_is_priced() -> None:
    euros = plan_return(price(7_900, "EUR"), GEL, *SEPTEMBER, estimate(109_000))
    free = plan_return(price(0), GEL, *SEPTEMBER, estimate(109_000))
    unpriced = plan_return(price(29_300), GEL, *SEPTEMBER, None)

    assert euros == NO_RETURN
    assert free == NO_RETURN
    assert (unpriced.plan_cost_minor, unpriced.return_multiple) == (29_300, None)


def test_the_monthly_price_comes_from_the_subscription_first() -> None:
    scene = ValueScene()
    sources = prices()
    local = monthly_plan_price(sources, scene.business)
    sources.subscription_repo.save(
        SubscriptionDocument(
            business_id=scene.business.id,
            plan_key=scene.business.plan_key,
            billing_period=BillingPeriod.ANNUAL,
            price_minor=351_000,  # type: ignore[arg-type]
            currency_code=GEL,
            status=SubscriptionStatus.ACTIVE,
            period_start=at("2026-09-01T00:00:00+04:00"),
            period_end=at("2027-09-01T00:00:00+04:00"),
        )
    )

    subscribed = monthly_plan_price(sources, scene.business)

    assert local is not None and local.currency_code == "GEL"
    assert subscribed == price(29_250)


def test_the_value_model_carries_the_multiple_and_staff_never_see_it() -> None:
    scene = ValueScene()
    lunch = scene.conversation("2026-09-10T13:00:00+04:00")
    for hour in range(13, 19):
        scene.booking(f"2026-09-10T{hour}:30:00+04:00", lunch, value=(20_000, "GEL"))
    world = scene.world
    compute = ComputeValueModelUseCase(
        business_repo=world.business_repo,
        business_profile_repo=world.profile_repo,
        schedule_exception_repo=world.exception_repo,
        sources=world.value_sources(),
        catalogs=world.catalogs(),
        plan_prices=prices(),
    )

    model = compute.run(
        ValueModelQuery(
            business_id=scene.business.id,
            date_from=LocalDate("2026-09-01"),
            date_to=LocalDate("2026-09-30"),
            previous_date_from=LocalDate("2026-08-01"),
            previous_date_to=LocalDate("2026-08-31"),
        )
    )

    local = PlanRegistry().find_local_monthly_price(scene.business.plan_key, GEL)
    assert local is not None
    assert model.plan_cost_minor == int(local.amount_minor)
    assert model.current.estimated_revenue_minor == 120_000
    assert model.return_multiple is not None and model.return_multiple > 0
    hidden = without_money(model)
    assert (hidden.plan_cost_minor, hidden.return_multiple) == (None, None)
