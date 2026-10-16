"""
The status page's ninety days: which UTC days they are, folding the
levels of one record into its day, and a component's history for the
page (today's own level counts before the job recorded it).
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

from typed_time_provider import Microseconds

from app.schemas.constants.platform_status import (
    StatusComponent,
    StatusLevel,
)
from app.schemas.domain.platform_status import (
    ComponentDayRecord,
    PlatformStatusDayDocument,
)
from app.schemas.dto.platform_status import StatusDayView
from app.schemas.typings.platform_status.constrained_integers import StatusCheckCount
from app.schemas.typings.platform_status.constrained_strings import StatusDay
from app.use_cases.platform_status.component_levels import worse

HISTORY_DAYS: int = 90
MICROSECONDS_PER_SECOND: int = 1_000_000


def status_day(moment: Microseconds) -> StatusDay:
    when: datetime = datetime.fromtimestamp(int(moment) / MICROSECONDS_PER_SECOND, UTC)
    return StatusDay(when.date().isoformat())


def history_days(now: Microseconds, count: int = HISTORY_DAYS) -> list[StatusDay]:
    """The last `count` UTC days, oldest first, today last."""

    today = datetime.fromtimestamp(int(now) / MICROSECONDS_PER_SECOND, UTC).date()
    return [
        StatusDay((today - timedelta(days=offset)).isoformat())
        for offset in range(count - 1, -1, -1)
    ]


def fold_levels(
    stored: PlatformStatusDayDocument | None,
    day: StatusDay,
    levels: Mapping[StatusComponent, StatusLevel],
    now: Microseconds,
) -> PlatformStatusDayDocument:
    """The day with one more record of every component's level."""

    records: dict[StatusComponent, ComponentDayRecord] = (
        {}
        if stored is None
        else {record.component: record for record in stored.components}
    )
    folded: list[ComponentDayRecord] = []
    for component in StatusComponent:
        level: StatusLevel = levels.get(component, StatusLevel.OPERATIONAL)
        record: ComponentDayRecord | None = records.get(component)
        folded.append(
            ComponentDayRecord(
                component=component,
                worst_level=(
                    level if record is None else worse(record.worst_level, level)
                ),
                check_count=StatusCheckCount(
                    (0 if record is None else int(record.check_count)) + 1
                ),
                degraded_count=StatusCheckCount(
                    (0 if record is None else int(record.degraded_count))
                    + (1 if level is StatusLevel.DEGRADED else 0)
                ),
                outage_count=StatusCheckCount(
                    (0 if record is None else int(record.outage_count))
                    + (1 if level is StatusLevel.OUTAGE else 0)
                ),
            )
        )
    return PlatformStatusDayDocument(
        day=day,
        components=folded,
        created_at=now if stored is None else stored.created_at,
        updated_at=now,
    )


def component_history(
    component: StatusComponent,
    days: Sequence[StatusDay],
    stored: Mapping[StatusDay, PlatformStatusDayDocument],
    today_level: StatusLevel,
) -> list[StatusDayView]:
    """Each day's worst level; a day nothing was recorded on is NO_DATA."""

    history: list[StatusDayView] = []
    last_index: int = len(days) - 1
    for index, day in enumerate(days):
        document: PlatformStatusDayDocument | None = stored.get(day)
        level: StatusLevel = StatusLevel.NO_DATA
        if document is not None:
            for record in document.components:
                if record.component is component:
                    level = record.worst_level
        if index == last_index:
            level = worse(level, today_level)
        history.append(StatusDayView(day=day, level=level))
    return history
