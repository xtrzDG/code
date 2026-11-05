"""What a bookable offer may carry: buffers, performers and seasonal rates."""

import pytest

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import SeasonalNightlyRate
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.knowledge.constrained_integers import (
    BufferMinutes,
    NightlyRateMinor,
)
from app.schemas.typings.knowledge.constrained_strings import SeasonDay
from app.utilities.knowledge.offer_checks import (
    MAX_SEASONS,
    check_buffer,
    check_performers_allowed,
    check_seasonal_rates,
    season_days,
)


def season(starts: str, ends: str, rate: int = 30000) -> SeasonalNightlyRate:
    return SeasonalNightlyRate(
        starts_on=SeasonDay(starts),
        ends_on=SeasonDay(ends),
        nightly_rate_minor=NightlyRateMinor(rate),
    )


def test_only_services_and_packages_keep_a_buffer() -> None:
    assert check_buffer(KnowledgeItemKind.SERVICE, BufferMinutes(15)) == 15
    assert check_buffer(KnowledgeItemKind.PACKAGE, BufferMinutes(10)) == 10
    # Zero is no buffer at all, for any kind.
    assert check_buffer(KnowledgeItemKind.MENU_ITEM, BufferMinutes(0)) is None
    assert check_buffer(KnowledgeItemKind.ROOM_TYPE, None) is None
    with pytest.raises(ValidationFailedError, match="Only services and packages"):
        check_buffer(KnowledgeItemKind.ROOM_TYPE, BufferMinutes(30))


def test_only_bookable_offers_have_performers() -> None:
    nino = ResourceId()

    assert check_performers_allowed(KnowledgeItemKind.SERVICE, [nino, nino]) == [nino]
    assert check_performers_allowed(KnowledgeItemKind.FAQ, []) == []
    with pytest.raises(ValidationFailedError, match="performed by resources"):
        check_performers_allowed(KnowledgeItemKind.MENU_ITEM, [nino])


def test_seasons_belong_to_room_types_and_never_overlap() -> None:
    summer = season("07-01", "08-31")
    holidays = season("12-20", "01-10", 35000)

    assert check_seasonal_rates(KnowledgeItemKind.ROOM_TYPE, [summer, holidays]) == [
        summer,
        holidays,
    ]
    assert check_seasonal_rates(KnowledgeItemKind.SERVICE, []) == []
    with pytest.raises(ValidationFailedError, match="Only room types"):
        check_seasonal_rates(KnowledgeItemKind.SERVICE, [summer])
    with pytest.raises(ValidationFailedError, match="both include 08-31"):
        check_seasonal_rates(
            KnowledgeItemKind.ROOM_TYPE, [summer, season("08-31", "09-15")]
        )
    with pytest.raises(ValidationFailedError, match="both include 01-01"):
        check_seasonal_rates(
            KnowledgeItemKind.ROOM_TYPE, [holidays, season("01-01", "01-02")]
        )


def test_a_room_type_has_at_most_24_seasons() -> None:
    monthly = [season(f"{month:02d}-01", f"{month:02d}-10") for month in range(1, 13)]
    later = [season(f"{month:02d}-11", f"{month:02d}-20") for month in range(1, 13)]
    extra = season("01-21", "01-25")

    assert len(check_seasonal_rates(KnowledgeItemKind.ROOM_TYPE, monthly + later)) == 24
    with pytest.raises(ValidationFailedError, match=f"at most {MAX_SEASONS}"):
        check_seasonal_rates(KnowledgeItemKind.ROOM_TYPE, [*monthly, *later, extra])


def test_season_days_wrap_over_new_year_and_count_leap_days() -> None:
    assert season_days(season("12-30", "01-02")) == [
        "01-01",
        "01-02",
        "12-30",
        "12-31",
    ]
    assert "02-29" in season_days(season("02-20", "03-05"))


@pytest.mark.parametrize("day", ["13-01", "02-30", "00-10", "1-01", "06-31"])
def test_a_season_day_is_a_real_month_and_day(day: str) -> None:
    with pytest.raises(ValueError):
        SeasonDay(day)
