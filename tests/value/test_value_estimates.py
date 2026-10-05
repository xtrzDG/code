"""How money is estimated per niche and currency, and which periods are asked."""

import pytest

from app.schemas.constants.niches import NicheKey
from app.schemas.constants.value import AverageCheckSource, ValueBasis, ValuePeriod
from app.schemas.dto.value.value_views import BusinessValueQuery
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.users.prefixed_id import UserId
from tests.billing.billing_registries import static_rate_registry
from tests.value.value_scene import ValueScene


def value_query(
    scene: ValueScene,
    period: ValuePeriod | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user_id: UserId | None = None,
) -> BusinessValueQuery:
    return BusinessValueQuery(
        user_id=user_id or scene.owner.id,
        business_id=scene.business.id,
        period=period,
        date_from=None if date_from is None else LocalDate(date_from),
        date_to=None if date_to is None else LocalDate(date_to),
    )


def test_a_euro_business_uses_the_typical_check_as_it_is() -> None:
    scene = ValueScene(currency_code="EUR", country_code="DE")

    model = scene.world.business_value().run(value_query(scene))

    assert model.average_check_source is AverageCheckSource.NICHE_DEFAULT
    assert model.average_check_minor == 4_000


def test_without_a_rate_there_is_no_money_estimate() -> None:
    scene = ValueScene(currency_code="USD", country_code="US")
    scene.world.exchange_rate_registry = static_rate_registry(
        [("EUR", "GEL", "2.9552")]
    )
    scene.booking(
        "2026-10-04T13:00:00+04:00", scene.conversation("2026-10-04T13:00:00+04:00")
    )

    model = scene.world.business_value().run(value_query(scene))

    assert model.average_check_source is AverageCheckSource.NONE
    assert model.average_check_minor is None and model.typical_check_minor is None
    assert model.current.assistant_booking_count == 1
    assert model.current.estimated_revenue_minor is None


@pytest.mark.parametrize(
    ("currency", "country", "rate", "typical_check_minor"),
    [("USD", "US", "1.1351", 4_500), ("JPY", "JP", "168.12", 6_700)],
)
def test_money_is_estimated_outside_euro_and_lari_with_the_euro_rate(
    currency: str, country: str, rate: str, typical_check_minor: int
) -> None:
    scene = ValueScene(currency_code=currency, country_code=country)
    scene.world.exchange_rate_registry = static_rate_registry([("EUR", currency, rate)])
    scene.booking(
        "2026-10-04T13:00:00+04:00", scene.conversation("2026-10-04T13:00:00+04:00")
    )

    model = scene.world.business_value().run(value_query(scene))

    assert model.average_check_source is AverageCheckSource.NICHE_DEFAULT
    assert model.typical_check_minor == typical_check_minor
    assert model.current.estimated_revenue_minor == typical_check_minor


def test_a_shop_earns_by_the_requests_it_takes() -> None:
    scene = ValueScene(
        niche_key=NicheKey.ONLINE_SHOP, currency_code="EUR", country_code="DE"
    )
    scene.lead("2026-10-03T13:00:00+04:00")
    scene.lead("2026-10-04T13:00:00+04:00")

    model = scene.world.business_value().run(
        value_query(scene, ValuePeriod.LAST_7_DAYS)
    )

    assert model.value_basis is ValueBasis.REQUESTS
    assert model.current.request_count == 2
    assert model.current.estimated_revenue_minor == 2 * 3_500


def test_a_niche_without_a_typical_check_waits_for_the_owners() -> None:
    scene = ValueScene(niche_key=NicheKey.REAL_ESTATE)

    model = scene.world.business_value().run(value_query(scene))

    assert model.average_check_source is AverageCheckSource.NONE
    assert model.current.estimated_revenue_minor is None


@pytest.mark.parametrize(
    ("period", "dates", "previous"),
    [
        (ValuePeriod.TODAY, ("2026-10-05", "2026-10-05"), ("2026-10-04", "2026-10-04")),
        (
            ValuePeriod.LAST_7_DAYS,
            ("2026-09-29", "2026-10-05"),
            ("2026-09-22", "2026-09-28"),
        ),
        (
            ValuePeriod.LAST_30_DAYS,
            ("2026-09-06", "2026-10-05"),
            ("2026-08-07", "2026-09-05"),
        ),
        (
            # The restaurant opened on 2026-08-01: 90 days would start before it.
            ValuePeriod.LAST_90_DAYS,
            ("2026-08-01", "2026-10-05"),
            ("2026-05-27", "2026-07-31"),
        ),
        (
            ValuePeriod.THIS_MONTH,
            ("2026-10-01", "2026-10-05"),
            ("2026-09-01", "2026-09-05"),
        ),
        (
            ValuePeriod.LAST_WEEK,
            ("2026-09-28", "2026-10-04"),
            ("2026-09-21", "2026-09-27"),
        ),
        (
            ValuePeriod.LAST_MONTH,
            ("2026-09-01", "2026-09-30"),
            ("2026-08-01", "2026-08-31"),
        ),
    ],
)
def test_named_periods_end_on_the_business_today(
    period: ValuePeriod,
    dates: tuple[str, str],
    previous: tuple[str, str],
) -> None:
    scene = ValueScene()  # Monday 2026-10-05, 12:00 in Tbilisi.

    model = scene.world.business_value().run(value_query(scene, period))

    assert (model.date_from, model.date_to) == dates
    assert (model.previous_date_from, model.previous_date_to) == previous


def test_local_dates_are_compared_with_as_many_days_before() -> None:
    scene = ValueScene()

    custom = scene.world.business_value().run(
        value_query(scene, date_from="2026-09-10", date_to="2026-09-19")
    )
    default = scene.world.business_value().run(value_query(scene))
    only_end = scene.world.business_value().run(
        value_query(scene, date_to="2026-09-30")
    )

    assert (custom.previous_date_from, custom.previous_date_to) == (
        "2026-08-31",
        "2026-09-09",
    )
    assert (default.date_from, default.date_to) == ("2026-09-06", "2026-10-05")
    assert (only_end.date_from, only_end.date_to) == ("2026-09-01", "2026-09-30")


@pytest.mark.parametrize(
    ("date_from", "date_to"),
    [("2026-10-02", "2026-10-01"), ("2025-01-01", "2026-10-01")],
)
def test_a_reversed_or_too_long_period_is_refused(date_from: str, date_to: str) -> None:
    scene = ValueScene()

    with pytest.raises(ValidationFailedError):
        scene.world.business_value().run(
            value_query(scene, date_from=date_from, date_to=date_to)
        )


def test_a_stranger_does_not_find_the_business() -> None:
    scene = ValueScene()

    with pytest.raises(NotFoundError):
        scene.world.business_value().run(value_query(scene, user_id=UserId()))
