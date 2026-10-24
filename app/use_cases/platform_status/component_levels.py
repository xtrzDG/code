"""
Each status component's level now: the platform alerts that fire (the
R10 alert rules, ops/alerts/*.yaml) and the announcements the platform
team wrote, whichever is worse.

An alert names the components whose customers it affects, and how badly
at its figure: model calls failing for half the turns is an outage of
every chat channel, a few failing is degraded service. Alerts about the
platform's inside (dead jobs, a handoff spike) affect no component.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformAlertCode, PlatformAlertStatus
from app.schemas.constants.platform_status import (
    STATUS_LEVEL_ORDER,
    AnnouncementLevel,
    AnnouncementStatus,
    StatusComponent,
    StatusLevel,
)
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.platform_status import PlatformAnnouncementDocument

CHAT_CHANNELS: tuple[StatusComponent, ...] = (
    StatusComponent.CHAT,
    StatusComponent.META,
    StatusComponent.TELEGRAM,
)
QUEUED_CHANNELS: tuple[StatusComponent, ...] = (
    StatusComponent.META,
    StatusComponent.TELEGRAM,
)


@dataclass(frozen=True)
class AlertImpact:
    """The components an alert affects, and the figure from which it is an outage."""

    components: tuple[StatusComponent, ...]
    outage_from: int | None = None


ALERT_IMPACTS: Mapping[PlatformAlertCode, AlertImpact] = {
    # Model calls fail: answers in every chat channel (percent of calls).
    PlatformAlertCode.LLM_ERRORS: AlertImpact(CHAT_CHANNELS, outage_from=50),
    # Customer messages wait for a worker (seconds the oldest waited).
    PlatformAlertCode.INBOUND_BACKLOG: AlertImpact(CHAT_CHANNELS, outage_from=900),
    # A worker stopped beating: answers slow down everywhere it served.
    PlatformAlertCode.STALE_WORKER: AlertImpact(CHAT_CHANNELS),
    # No worker beats at all: nobody gets an answer in any chat channel.
    PlatformAlertCode.WORKER_DOWN: AlertImpact(CHAT_CHANNELS, outage_from=0),
    # Replies to messengers fail for good (percent of the outbox).
    PlatformAlertCode.OUTBOUND_FAILURES: AlertImpact(QUEUED_CHANNELS, outage_from=50),
    # Bookings and prices fail inside answers and calls.
    PlatformAlertCode.TOOL_ERRORS: AlertImpact((*CHAT_CHANNELS, StatusComponent.VOICE)),
    # Login codes refused by a platform cap: signing in to the cabinet.
    PlatformAlertCode.OTP_CAP_TRIPS: AlertImpact((StatusComponent.CABINET,)),
}

ANNOUNCEMENT_LEVELS: Mapping[AnnouncementLevel, StatusLevel | None] = {
    AnnouncementLevel.INFO: None,
    AnnouncementLevel.MAINTENANCE: StatusLevel.MAINTENANCE,
    AnnouncementLevel.DEGRADED: StatusLevel.DEGRADED,
    AnnouncementLevel.OUTAGE: StatusLevel.OUTAGE,
}


def worse(left: StatusLevel, right: StatusLevel) -> StatusLevel:
    return left if STATUS_LEVEL_ORDER[left] >= STATUS_LEVEL_ORDER[right] else right


def worst(levels: Iterable[StatusLevel]) -> StatusLevel:
    result: StatusLevel = StatusLevel.OPERATIONAL
    for level in levels:
        result = worse(result, level)
    return result


def alert_levels(
    states: Iterable[PlatformAlertStateDocument],
) -> dict[StatusComponent, StatusLevel]:
    levels: dict[StatusComponent, StatusLevel] = {
        component: StatusLevel.OPERATIONAL for component in StatusComponent
    }
    for state in states:
        impact: AlertImpact | None = ALERT_IMPACTS.get(state.code)
        if impact is None or state.status is not PlatformAlertStatus.FIRING:
            continue
        is_outage: bool = impact.outage_from is not None and int(state.figure) >= (
            impact.outage_from
        )
        level: StatusLevel = StatusLevel.OUTAGE if is_outage else StatusLevel.DEGRADED
        for component in impact.components:
            levels[component] = worse(levels[component], level)
    return levels


def is_in_effect(announcement: PlatformAnnouncementDocument, now: Microseconds) -> bool:
    """Active and started (planned maintenance counts from its start)."""

    return announcement.status is AnnouncementStatus.ACTIVE and int(
        announcement.starts_at
    ) <= int(now)


def current_levels(
    states: Iterable[PlatformAlertStateDocument],
    announcements: Iterable[PlatformAnnouncementDocument],
    now: Microseconds,
) -> dict[StatusComponent, StatusLevel]:
    levels: dict[StatusComponent, StatusLevel] = alert_levels(states)
    for announcement in announcements:
        level: StatusLevel | None = ANNOUNCEMENT_LEVELS[announcement.level]
        if level is None or not is_in_effect(announcement, now):
            continue
        for component in announcement.components:
            levels[component] = worse(levels[component], level)
    return levels
