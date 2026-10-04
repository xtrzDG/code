"""
GET /v1/platform/status's use case and the job that records the history:
components now, ninety days of bars, announcements in the reader's language.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    AnnouncementStatus,
    StatusComponent,
    StatusLevel,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.platform_status import PlatformStatusQuery, PlatformStatusView
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.platform_status.get_platform_status_use_case import (
    GetPlatformStatusUseCase,
)
from app.use_cases.platform_status.record_platform_status_use_case import (
    RecordPlatformStatusUseCase,
)
from tests.platform_status.status_world import DAY, HOUR, MINUTE, StatusWorld

TICK = JobTick(job_name=JobName("record_platform_status"), scheduled_at=Microseconds(0))


def status(world: StatusWorld, language: str | None = None) -> PlatformStatusView:
    return GetPlatformStatusUseCase(
        world.alert_repo,
        world.announcement_repo,
        world.day_repo,
        world.clock.wall_clock,
    ).run(
        PlatformStatusQuery(
            language=None if language is None else LanguageTag(language)
        )
    )


def record(world: StatusWorld) -> int:
    report = RecordPlatformStatusUseCase(
        world.alert_repo,
        world.announcement_repo,
        world.day_repo,
        world.clock.wall_clock,
    ).run(TICK)
    return int(report.processed_count)


def component(view: PlatformStatusView, name: StatusComponent) -> StatusLevel:
    return next(item.level for item in view.components if item.component is name)


def test_a_quiet_platform_is_operational_with_no_history_yet() -> None:
    view = status(StatusWorld())

    assert view.level is StatusLevel.OPERATIONAL
    assert view.checked_at is None
    assert [item.component for item in view.components] == list(StatusComponent)
    assert all(len(item.history) == 90 for item in view.components)
    history = view.components[0].history
    assert history[0].level is StatusLevel.NO_DATA
    assert history[-1].level is StatusLevel.OPERATIONAL  # today counts now
    assert view.announcements == [] and view.past_announcements == []


def test_a_firing_alert_shows_on_its_components_and_overall() -> None:
    world = StatusWorld()
    world.fire(PlatformAlertCode.OUTBOUND_FAILURES, 60)

    view = status(world)

    assert view.level is StatusLevel.OUTAGE
    assert view.checked_at == world.now
    assert component(view, StatusComponent.META) is StatusLevel.OUTAGE
    assert component(view, StatusComponent.CHAT) is StatusLevel.OPERATIONAL


def test_the_job_keeps_the_worst_of_each_day() -> None:
    world = StatusWorld()
    world.fire(PlatformAlertCode.LLM_ERRORS, 30)
    assert record(world) == len(StatusComponent)
    world.clock.advance(10 * MINUTE)
    world.resolve(PlatformAlertCode.LLM_ERRORS)
    record(world)
    world.clock.advance(DAY)
    record(world)

    view = status(world)

    chat = next(
        item for item in view.components if item.component is StatusComponent.CHAT
    )
    assert chat.level is StatusLevel.OPERATIONAL
    assert [day.level for day in chat.history[-3:]] == [
        StatusLevel.NO_DATA,
        StatusLevel.DEGRADED,
        StatusLevel.OPERATIONAL,
    ]
    [today] = world.day_repo.get_many([chat.history[-1].day])
    assert int(today.components[0].check_count) == 1


def test_announcements_are_shown_in_the_readers_language() -> None:
    world = StatusWorld()
    world.announce(AnnouncementLevel.DEGRADED, [StatusComponent.META])

    russian = status(world, "ru")
    georgian = status(world, "ka")
    english = status(world)

    assert russian.announcements[0].text == "Задержки."
    assert russian.announcements[0].language == "ru"
    assert georgian.announcements[0].language == "en"
    assert english.announcements[0].text == "WhatsApp replies are delayed."
    assert component(russian, StatusComponent.META) is StatusLevel.DEGRADED


def test_planned_maintenance_is_announced_before_it_counts() -> None:
    world = StatusWorld()
    world.announce(
        AnnouncementLevel.MAINTENANCE, [StatusComponent.CABINET], starts_in=2 * HOUR
    )

    view = status(world)

    assert view.announcements[0].is_scheduled is True
    assert component(view, StatusComponent.CABINET) is StatusLevel.OPERATIONAL


def test_resolved_announcements_stay_listed_for_ninety_days() -> None:
    world = StatusWorld()
    old = world.announce(AnnouncementLevel.OUTAGE, [StatusComponent.VOICE])
    old.status = AnnouncementStatus.RESOLVED
    old.resolved_at = Microseconds(world.now)
    world.announcement_repo.save(old)
    world.clock.advance(HOUR)
    recent = world.announce(AnnouncementLevel.DEGRADED, [StatusComponent.CHAT])
    recent.status = AnnouncementStatus.RESOLVED
    recent.resolved_at = Microseconds(world.now)
    world.announcement_repo.save(recent)

    listed = status(world)
    world.clock.advance(91 * DAY)
    later = status(world)

    assert listed.announcements == []
    assert [item.id for item in listed.past_announcements] == [recent.id, old.id]
    assert component(listed, StatusComponent.VOICE) is StatusLevel.OPERATIONAL
    assert later.past_announcements == []
