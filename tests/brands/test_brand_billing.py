"""
Billing a brand: a further location pays the plan's additional-location
price, the first one the plan price; one setup fee for the whole brand.
"""

from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import BillingPeriod, PlanKey
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.brand_billing import (
    is_additional_location,
    owes_brand_setup_fee,
)
from app.use_cases.shared.subscription_pricing import price_subscription
from tests.billing.billing_registries import PriceBookPlanRegistry
from tests.brands.brand_builders import (
    build_brand,
    build_location,
    in_memory_business_repo,
)
from tests.foundation.brand_repositories import in_memory_brand_repo

OWNER = UserId()
EUR = CurrencyCode("EUR")
GEL = CurrencyCode("GEL")


def test_a_further_location_pays_the_additional_location_price() -> None:
    plans = PlanRegistry()

    for plan_key, full, further in (
        (PlanKey.CHAT, 9900, 6900),
        (PlanKey.VOICE_AND_CHAT, 17500, 12500),
        (PlanKey.PLUS, 34900, 24900),
    ):
        monthly = BillingPeriod.MONTHLY
        assert price_subscription(plans, plan_key, monthly, EUR).amount_minor == full
        assert (
            price_subscription(plans, plan_key, monthly, EUR, True).amount_minor
            == further
        )

    plus_in_lari = price_subscription(
        plans, PlanKey.PLUS, BillingPeriod.MONTHLY, GEL, True
    )
    assert (plus_in_lari.amount_minor, plus_in_lari.currency_code) == (73500, GEL)
    # A year is twelve further-location months less the annual discount.
    annual = price_subscription(plans, PlanKey.PLUS, BillingPeriod.ANNUAL, EUR, True)
    assert annual.amount_minor == 253980


def test_without_a_location_price_in_the_currency_the_plan_price_is_billed() -> None:
    plans = PriceBookPlanRegistry({(PlanKey.CHAT, "JPY"): 1500000})
    yen = CurrencyCode("JPY")

    price = price_subscription(plans, PlanKey.CHAT, BillingPeriod.MONTHLY, yen, True)

    assert (price.amount_minor, price.currency_code) == (1500000, yen)


def test_only_the_first_location_carries_the_one_setup_fee() -> None:
    brand = build_brand(OWNER)
    business_repo = in_memory_business_repo()
    brand_repo = in_memory_brand_repo()
    brand_repo.add(brand)
    first = build_location(brand, OWNER, created_at=10)
    later = build_location(brand, OWNER, created_at=20)
    alone = build_location(None, OWNER, created_at=5)
    for location in (first, later, alone):
        business_repo.save(location)

    assert is_additional_location(business_repo, first) is False
    assert is_additional_location(business_repo, later) is True
    assert is_additional_location(business_repo, alone) is False
    assert owes_brand_setup_fee(brand_repo, business_repo, alone) is True
    assert owes_brand_setup_fee(brand_repo, business_repo, later) is False
    assert owes_brand_setup_fee(brand_repo, business_repo, first) is True
    # Asked again (the invoice retried), the holder still owes it.
    assert owes_brand_setup_fee(brand_repo, business_repo, first) is True


def test_a_location_that_becomes_first_after_the_claim_owes_nothing() -> None:
    brand = build_brand(OWNER)
    business_repo = in_memory_business_repo()
    brand_repo = in_memory_brand_repo()
    brand_repo.add(brand)
    first = build_location(brand, OWNER, created_at=10)
    later = build_location(brand, OWNER, created_at=20)
    for location in (first, later):
        business_repo.save(location)
    assert owes_brand_setup_fee(brand_repo, business_repo, first) is True

    # The first location leaves the brand; the second is now its first.
    business_repo.save(first.model_copy(update={"brand_id": None}))

    assert is_additional_location(business_repo, later) is False
    assert owes_brand_setup_fee(brand_repo, business_repo, later) is False
