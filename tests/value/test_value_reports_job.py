"""The hourly job of the owners' digests and monthly reports."""

from datetime import datetime

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.value import ValueReportDelivery, ValueReportKind
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.domain.value_settings import DigestPreferencesDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from app.utilities.value.value_keys import digest_preferences_id_of
from tests.notifications.staff_alert_fakes import TEST_ENCRYPTION_KEY
from tests.operations.fakes import to_microseconds
from tests.value.value_scene import OWNER_EMAIL, ValueScene

TICK: JobTick = JobTick(
    job_name=JobName("send_value_reports"),
    scheduled_at=to_microseconds(datetime.fromisoformat("2026-10-05T08:00:00+00:00")),
)


def run_job(scene: ValueScene) -> int:
    return int(scene.world.send_value_reports().run(TICK).processed_count)


def reports(scene: ValueScene, kind: ValueReportKind) -> list[ValueReportDocument]:
    return scene.world.value_report_repo.page_by_business(
        scene.business.id, kind, KeysetSlice(limit=KeysetReadLimit(10))
    )


def active_scene() -> ValueScene:
    """Bookings last week (Sep 28 to Oct 4) and in September."""

    scene = ValueScene()
    for day in ("2026-09-15", "2026-09-29", "2026-10-02"):
        chat = scene.conversation(f"{day}T13:00:00+04:00")
        scene.message(chat, f"{day}T13:01:00+04:00")
        scene.booking(f"{day}T13:05:00+04:00", chat)

    return scene


def choose(scene: ValueScene, daily: bool, weekly: bool, monthly: bool) -> None:
    scene.world.digest_preferences_repo.save(
        DigestPreferencesDocument(
            id=digest_preferences_id_of(scene.business.id, scene.owner.id),
            business_id=scene.business.id,
            user_id=scene.owner.id,
            is_daily_digest_on=daily,
            is_weekly_digest_on=weekly,
            is_monthly_report_on=monthly,
        )
    )


def test_on_monday_the_week_and_the_month_go_out_once() -> None:
    scene = active_scene()
    scene.device(scene.owner, "ka")

    stored = run_job(scene)
    again = run_job(scene)

    assert (stored, again) == (2, 0)
    [weekly] = reports(scene, ValueReportKind.WEEKLY)
    [monthly] = reports(scene, ValueReportKind.MONTHLY)
    assert (weekly.period_key, weekly.date_from, weekly.date_to) == (
        "2026-W40",
        "2026-09-28",
        "2026-10-04",
    )
    assert (monthly.period_key, monthly.date_from) == ("2026-09", "2026-09-01")
    assert weekly.current.assistant_booking_count == 2
    assert monthly.current.assistant_booking_count == 2
    assert weekly.delivery is ValueReportDelivery.SENT
    assert weekly.recipient_count == 2  # the e-mail and the device
    emails = scene.world.notifier.notifications
    assert [str(note.contact.address) for note in emails] == [OWNER_EMAIL] * 2
    assert {note.contact.channel for note in emails} == {ManagerContactChannel.EMAIL}
    assert {str(note.subject) for note in emails} == {
        f"value_report:{weekly.id}",
        f"value_report:{monthly.id}",
    }
    assert len(scene.world.push_queue.queued) == 2
    assert scene.world.push_queue.queued[0].brief.title.startswith("თქვენი")
    assert scene.world.notifier.notifications[0].contact.language == "ru"


def test_the_link_opens_the_report() -> None:
    scene = active_scene()

    run_job(scene)

    text = str(scene.world.notifier.notifications[0].text)
    link_line = next(line for line in text.split("\n") if "/n/" in line)
    token = link_line.rsplit("/n/", 1)[1]
    claims = StaffLinkSigner(TEST_ENCRYPTION_KEY).read(StaffLinkToken(token))
    assert claims is not None
    assert claims.target is StaffLinkTarget.REPORT
    assert claims.value_report_id in {
        report.id
        for kind in (ValueReportKind.WEEKLY, ValueReportKind.MONTHLY)
        for report in reports(scene, kind)
    }


def test_before_nine_on_monday_the_week_waits() -> None:
    scene = active_scene()
    scene.world.clock.move_to(datetime.fromisoformat("2026-10-05T08:30:00+04:00"))

    run_job(scene)

    assert reports(scene, ValueReportKind.WEEKLY) == []
    assert len(reports(scene, ValueReportKind.MONTHLY)) == 1


def test_a_quiet_period_is_stored_and_not_sent() -> None:
    scene = ValueScene()

    assert run_job(scene) == 2
    assert {
        report.delivery
        for kind in (ValueReportKind.WEEKLY, ValueReportKind.MONTHLY)
        for report in reports(scene, kind)
    } == {ValueReportDelivery.QUIET}
    assert scene.world.notifier.notifications == []


def test_the_daily_digest_comes_only_to_those_who_turned_it_on() -> None:
    scene = active_scene()
    choose(scene, daily=True, weekly=False, monthly=True)
    yesterday = scene.conversation("2026-10-04T14:00:00+04:00")
    scene.booking("2026-10-04T14:05:00+04:00", yesterday)

    run_job(scene)

    [daily] = reports(scene, ValueReportKind.DAILY)
    [weekly] = reports(scene, ValueReportKind.WEEKLY)
    assert (daily.period_key, daily.previous_date_from) == ("2026-10-04", "2026-10-03")
    assert daily.delivery is ValueReportDelivery.SENT
    assert weekly.delivery is ValueReportDelivery.NO_RECIPIENTS
    assert len(scene.world.notifier.notifications) == 2  # daily and monthly


def test_without_a_wish_for_it_no_daily_digest_is_made() -> None:
    scene = active_scene()

    run_job(scene)

    assert reports(scene, ValueReportKind.DAILY) == []


def test_periods_before_the_business_existed_are_skipped() -> None:
    scene = active_scene()
    scene.business.created_at = to_microseconds(
        datetime.fromisoformat("2026-10-01T09:00:00+04:00")
    )
    scene.world.business_repo.save(scene.business)

    run_job(scene)

    assert reports(scene, ValueReportKind.MONTHLY) == []
    assert len(reports(scene, ValueReportKind.WEEKLY)) == 1


def test_a_paused_business_gets_its_month_but_no_week() -> None:
    scene = active_scene()
    scene.business.status = BusinessStatus.PAUSED
    scene.world.business_repo.save(scene.business)

    run_job(scene)

    assert reports(scene, ValueReportKind.WEEKLY) == []
    assert len(reports(scene, ValueReportKind.MONTHLY)) == 1


def test_a_business_still_being_set_up_gets_nothing() -> None:
    scene = active_scene()
    scene.business.status = BusinessStatus.ONBOARDING
    scene.world.business_repo.save(scene.business)

    assert run_job(scene) == 0
