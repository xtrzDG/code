"""The ninety days: UTC days, folding records into a day, a component's bars."""

from typed_time_provider import Microseconds

from app.schemas.constants.platform_status import StatusComponent, StatusLevel
from app.schemas.typings.platform_status.constrained_strings import StatusDay
from app.use_cases.platform_status.status_history import (
    component_history,
    fold_levels,
    history_days,
    status_day,
)

# 2026-09-21T12:26:40Z
NOW = Microseconds(1_790_000_000_000_000)
TODAY = StatusDay("2026-09-21")


def test_days_are_utc_calendar_days_oldest_first() -> None:
    days = history_days(NOW)

    assert status_day(NOW) == TODAY
    assert len(days) == 90
    assert days[-1] == TODAY
    assert days[0] == "2026-06-24"
    assert days == sorted(days)


def test_a_day_keeps_its_worst_level_and_counts_its_records() -> None:
    first = fold_levels(None, TODAY, {StatusComponent.META: StatusLevel.OUTAGE}, NOW)
    second = fold_levels(
        first, TODAY, {StatusComponent.META: StatusLevel.DEGRADED}, NOW
    )
    third = fold_levels(second, TODAY, {}, Microseconds(int(NOW) + 1))

    [meta] = [record for record in third.components if record.component.value == "meta"]
    assert meta.worst_level is StatusLevel.OUTAGE
    assert (
        int(meta.check_count),
        int(meta.degraded_count),
        int(meta.outage_count),
    ) == (
        3,
        1,
        1,
    )
    assert len(third.components) == len(StatusComponent)
    assert third.created_at == NOW and third.updated_at == int(NOW) + 1


def test_a_component_history_marks_days_without_records_and_counts_today() -> None:
    days = [StatusDay("2026-09-19"), StatusDay("2026-09-20"), TODAY]
    stored = {
        StatusDay("2026-09-20"): fold_levels(
            None,
            StatusDay("2026-09-20"),
            {StatusComponent.TELEGRAM: StatusLevel.DEGRADED},
            NOW,
        )
    }

    history = component_history(
        StatusComponent.TELEGRAM, days, stored, StatusLevel.MAINTENANCE
    )
    voice = component_history(
        StatusComponent.VOICE, days, stored, StatusLevel.OPERATIONAL
    )

    assert [day.level for day in history] == [
        StatusLevel.NO_DATA,
        StatusLevel.DEGRADED,
        StatusLevel.MAINTENANCE,
    ]
    assert [day.level for day in voice] == [
        StatusLevel.NO_DATA,
        StatusLevel.OPERATIONAL,
        StatusLevel.OPERATIONAL,
    ]
