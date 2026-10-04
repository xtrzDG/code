from typed_time_provider import Microseconds, WallClock

from app.contracts.monitoring import PlatformAlertStateRepoContract
from app.contracts.platform_status import (
    PlatformAnnouncementRepoContract,
    PlatformStatusDayRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.constants.platform_status import StatusComponent, StatusLevel
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.platform_status import (
    PlatformAnnouncementDocument,
    PlatformStatusDayDocument,
)
from app.schemas.dto.platform_status import (
    ComponentStatusView,
    PlatformStatusQuery,
    PlatformStatusView,
)
from app.schemas.typings.platform_status.constrained_strings import StatusDay
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.platform_status.announcement_views import public_view
from app.use_cases.platform_status.component_levels import current_levels, worst
from app.use_cases.platform_status.status_history import (
    HISTORY_DAYS,
    component_history,
    history_days,
)

MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
ACTIVE_ANNOUNCEMENT_LIMIT: DocumentQueryLimit = DocumentQueryLimit(50)
PAST_ANNOUNCEMENT_LIMIT: DocumentQueryLimit = DocumentQueryLimit(20)


class GetPlatformStatusUseCase(
    UseCaseContract[PlatformStatusQuery, PlatformStatusView]
):
    """
    GET /v1/platform/status (public): every component's level now, from
    the platform alerts that fire and the announcements in effect
    (component_levels.py), its last ninety days, the announcements shown
    now (planned maintenance before its start too) and those resolved in
    the last ninety days. A handful of keyed and indexed reads.
    """

    def __init__(
        self,
        alert_state_repo: PlatformAlertStateRepoContract,
        announcement_repo: PlatformAnnouncementRepoContract,
        status_day_repo: PlatformStatusDayRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._alert_state_repo: PlatformAlertStateRepoContract = alert_state_repo
        self._announcement_repo: PlatformAnnouncementRepoContract = announcement_repo
        self._status_day_repo: PlatformStatusDayRepoContract = status_day_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PlatformStatusQuery) -> PlatformStatusView:
        now: Microseconds = self._wall_clock.now_unix()
        states: list[PlatformAlertStateDocument] = self._alert_state_repo.get_many(
            list(PlatformAlertCode)
        )
        active: list[PlatformAnnouncementDocument] = sorted(
            self._announcement_repo.list_active(ACTIVE_ANNOUNCEMENT_LIMIT),
            key=lambda announcement: -int(announcement.starts_at),
        )
        resolved: list[PlatformAnnouncementDocument] = (
            self._announcement_repo.list_resolved_since(
                Microseconds(int(now) - HISTORY_DAYS * MICROSECONDS_PER_DAY),
                PAST_ANNOUNCEMENT_LIMIT,
            )
        )
        levels: dict[StatusComponent, StatusLevel] = current_levels(states, active, now)
        days: list[StatusDay] = history_days(now)
        stored: dict[StatusDay, PlatformStatusDayDocument] = {
            document.day: document for document in self._status_day_repo.get_many(days)
        }
        checks: list[int] = [int(state.checked_at) for state in states]
        return PlatformStatusView(
            level=worst(levels.values()),
            checked_at=Microseconds(max(checks)) if checks else None,
            components=[
                ComponentStatusView(
                    component=component,
                    level=levels[component],
                    history=component_history(
                        component, days, stored, levels[component]
                    ),
                )
                for component in StatusComponent
            ],
            announcements=[
                public_view(announcement, input_data.language, now)
                for announcement in active
            ],
            past_announcements=[
                public_view(announcement, input_data.language, now)
                for announcement in resolved
            ],
        )
