"""Each component's level: the alerts that fire and the announcements in effect."""

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformAlertCode, PlatformAlertStatus
from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    AnnouncementStatus,
    StatusComponent,
    StatusLevel,
)
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.platform_status import PlatformAnnouncementDocument
from app.use_cases.platform_status.component_levels import (
    ALERT_IMPACTS,
    current_levels,
    worst,
)
from tests.platform_status.status_world import HOUR, alert, announcement

NOW: int = 1_790_000_000_000_000
CHAT, META, TELEGRAM, VOICE, CABINET = (
    StatusComponent.CHAT,
    StatusComponent.META,
    StatusComponent.TELEGRAM,
    StatusComponent.VOICE,
    StatusComponent.CABINET,
)
OK, DEGRADED, OUTAGE = StatusLevel.OPERATIONAL, StatusLevel.DEGRADED, StatusLevel.OUTAGE


def levels(
    *states: PlatformAlertStateDocument,
    notices: tuple[PlatformAnnouncementDocument, ...] = (),
) -> dict[StatusComponent, StatusLevel]:
    return current_levels(states, notices, Microseconds(NOW))


def test_without_alerts_everything_works() -> None:
    assert set(levels().values()) == {OK}
    assert worst([]) is OK


def test_failing_model_calls_degrade_every_chat_channel_and_half_is_an_outage() -> None:
    some = levels(alert(PlatformAlertCode.LLM_ERRORS, 20, NOW))
    half = levels(alert(PlatformAlertCode.LLM_ERRORS, 50, NOW))

    assert [some[CHAT], some[META], some[TELEGRAM]] == [DEGRADED] * 3
    assert some[VOICE] is OK and some[CABINET] is OK
    assert [half[CHAT], half[META], half[TELEGRAM]] == [OUTAGE] * 3


def test_failing_deliveries_touch_only_the_messengers() -> None:
    result = levels(alert(PlatformAlertCode.OUTBOUND_FAILURES, 12, NOW))

    assert result[META] is DEGRADED and result[TELEGRAM] is DEGRADED
    assert result[CHAT] is OK


def test_refused_login_codes_degrade_the_cabinet() -> None:
    assert levels(alert(PlatformAlertCode.OTP_CAP_TRIPS, 3, NOW))[CABINET] is DEGRADED


def test_inside_alerts_and_resolved_ones_are_not_shown() -> None:
    result = levels(
        alert(PlatformAlertCode.DEAD_JOBS, 9, NOW),
        alert(PlatformAlertCode.HANDOFF_SPIKE, 30, NOW),
        alert(PlatformAlertCode.LLM_ERRORS, 90, NOW, PlatformAlertStatus.RESOLVED),
    )

    assert set(result.values()) == {OK}
    assert PlatformAlertCode.DEAD_JOBS not in ALERT_IMPACTS


def test_an_announcement_counts_from_its_start_and_never_softens_an_alert() -> None:
    outage = announcement(AnnouncementLevel.OUTAGE, [VOICE], NOW - HOUR)
    planned = announcement(AnnouncementLevel.MAINTENANCE, [CABINET], NOW + HOUR)
    notice = announcement(AnnouncementLevel.INFO, [CHAT], NOW - HOUR)
    mild = announcement(AnnouncementLevel.DEGRADED, [META], NOW - HOUR)

    result = levels(
        alert(PlatformAlertCode.OUTBOUND_FAILURES, 80, NOW),
        notices=(outage, planned, notice, mild),
    )

    assert result[VOICE] is OUTAGE
    assert result[CABINET] is OK
    assert result[CHAT] is OK
    assert result[META] is OUTAGE
    assert worst(result.values()) is OUTAGE


def test_a_resolved_announcement_no_longer_counts() -> None:
    resolved = announcement(AnnouncementLevel.OUTAGE, [VOICE], NOW - HOUR)
    resolved.status = AnnouncementStatus.RESOLVED

    assert levels(notices=(resolved,))[VOICE] is OK


def test_maintenance_is_its_own_level() -> None:
    planned = announcement(AnnouncementLevel.MAINTENANCE, [CABINET], NOW)

    assert levels(notices=(planned,))[CABINET] is StatusLevel.MAINTENANCE
