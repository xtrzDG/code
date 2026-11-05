"""
The episodes of a platform alert and its cooldown: what one check changes
in the stored state, and whether the team is told about it.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import AlertNoticeKind, PlatformAlertStatus
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.typings.monitoring.constrained_integers import (
    AlertCooldownMinutes,
    NotificationCount,
)

MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000


@dataclass(frozen=True)
class EpisodeStep:
    """The state to store after a check, and the notice it sends (or none)."""

    state: PlatformAlertStateDocument
    notice: AlertNoticeKind | None = None


def next_episode_step(
    stored: PlatformAlertStateDocument | None,
    observation: AlertObservation,
    now: Microseconds,
    cooldown: AlertCooldownMinutes,
) -> EpisodeStep | None:
    """
    - A firing check starts an episode (told at once) unless one is on;
      an episode that is on is told again once the cooldown has passed
      since the last notice, else only its figure is updated.
    - A quiet check ends the episode that is on (told once).
    - A quiet check without an episode changes nothing (None: no write).
    """

    is_on: bool = stored is not None and stored.status is PlatformAlertStatus.FIRING
    if not observation.is_firing:
        if stored is None or not is_on:
            return None

        return EpisodeStep(
            state=_checked(stored, observation, now).model_copy(
                update={"status": PlatformAlertStatus.RESOLVED, "resolved_at": now}
            ),
            notice=AlertNoticeKind.RESOLVED,
        )

    if stored is None or not is_on:
        return EpisodeStep(
            state=PlatformAlertStateDocument(
                code=observation.code,
                status=PlatformAlertStatus.FIRING,
                figure=observation.figure,
                threshold=observation.threshold,
                unit=observation.unit,
                detail=observation.detail,
                fired_at=now,
                checked_at=now,
                notified_at=now,
                notification_count=NotificationCount(1),
                created_at=now if stored is None else stored.created_at,
                updated_at=now,
            ),
            notice=AlertNoticeKind.FIRING,
        )

    checked: PlatformAlertStateDocument = _checked(stored, observation, now)
    last_notice: int = int(stored.notified_at or stored.fired_at)
    if int(now) - last_notice < int(cooldown) * MICROSECONDS_PER_MINUTE:
        return EpisodeStep(state=checked)

    return EpisodeStep(
        state=checked.model_copy(
            update={
                "notified_at": now,
                "notification_count": NotificationCount(
                    int(stored.notification_count) + 1
                ),
            }
        ),
        notice=AlertNoticeKind.STILL_FIRING,
    )


def _checked(
    stored: PlatformAlertStateDocument,
    observation: AlertObservation,
    now: Microseconds,
) -> PlatformAlertStateDocument:
    return stored.model_copy(
        update={
            "figure": observation.figure,
            "threshold": observation.threshold,
            "unit": observation.unit,
            "detail": observation.detail,
            "checked_at": now,
            "updated_at": now,
        }
    )
