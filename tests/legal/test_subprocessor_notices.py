"""
The daily notices job (DPA section 8.3): the owners of every business hear
of an announced sub-processor change on the day its 30-day notice period
opens, once, by e-mail or else SMS, in their language; each business's audit
log records it; staff are not told; a missed notice still goes out, marked
late, until the notice period after the change has passed.
"""

from app.registries.legal.subprocessor_catalog import SUBPROCESSORS
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.legal import SubprocessorChangeKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.legal import SubprocessorNoticeDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.platform.constrained_strings import JobName
from tests.legal.legal_world import (
    NoticeWorld,
    announced_entry,
    business,
    moment,
    put,
    retiring_entry,
    user,
)

ADDITION = announced_entry("mailbox", added_on="2026-12-01", announced_on="2026-10-20")


def tick(world: NoticeWorld) -> int:
    report = world.job.run(
        JobTick(
            job_name=JobName("send_subprocessor_notices"),
            scheduled_at=world.clock.wall_clock.now_unix(),
        )
    )
    return int(report.processed_count)


def notices(world: NoticeWorld) -> list[SubprocessorNoticeDocument]:
    return list(world.notices.list_all())


def test_nothing_goes_out_before_the_notice_period_opens() -> None:
    world = NoticeWorld((*SUBPROCESSORS, ADDITION), today="2026-10-31")

    assert tick(world) == 0
    assert world.notifier.sent == []
    assert list(world.announcements.list_all()) == []


def test_owners_hear_thirty_days_ahead_once_in_their_language() -> None:
    world = NoticeWorld((*SUBPROCESSORS, ADDITION), today="2026-11-01")

    assert tick(world) == 2

    sent = {str(item.contact.address): item for item in world.notifier.sent}
    assert set(sent) == {"nino@salon.example", "+995555123456", "owner@cafe.example"}
    assert sent["+995555123456"].contact.channel is ManagerContactChannel.SMS
    russian = str(sent["nino@salon.example"].text)
    assert russian.startswith("Новый субобработчик с 2026-12-01: Почта ЕС")
    assert "Salon Ia" in russian and "возразить" in russian
    assert str(sent["+995555123456"].text).startswith(
        "ახალი ქვე-უფლებამოსილი პირი 2026-12-01-დან: ფოსტა ევროკავშირი"
    )
    # en-GB reads English.
    assert str(sent["owner@cafe.example"].text).startswith(
        "New sub-processor from 2026-12-01: Mailbox EU"
    )
    assert {str(item.subject) for item in world.notifier.sent} == {
        "subprocessor:mailbox-added-2026-12-01"
    }

    recorded = notices(world)
    assert {notice.business_id for notice in recorded} == {
        world.salon.id,
        world.cafe.id,
    }
    assert all(notice.kind is SubprocessorChangeKind.ADDED for notice in recorded)
    assert all(not notice.is_late for notice in recorded)
    assert sorted(int(notice.recipient_count) for notice in recorded) == [1, 2]

    entries = list(world.audit.list_all())
    assert {entry.business_id for entry in entries} == {world.salon.id, world.cafe.id}
    assert all(
        entry.action is AuditAction.CREATE
        and str(entry.entity) == "subprocessor_notice"
        and str(entry.entity_id) == "mailbox-added-2026-12-01"
        and entry.actor_id is None
        for entry in entries
    )
    (announcement,) = world.announcements.list_all()
    assert announcement.completed_at is not None
    assert int(announcement.notified_business_count) == 2
    assert int(announcement.recipient_count) == 3

    world.clock.set("2026-11-02")
    assert tick(world) == 0
    assert len(world.notifier.sent) == 3
    assert len(list(world.audit.list_all())) == 2


def test_a_business_created_after_the_announcement_reads_the_table_instead() -> None:
    world = NoticeWorld((*SUBPROCESSORS, ADDITION), today="2026-11-01")
    tick(world)
    newcomer = user("en", email="new@bakery.example")
    put(world.users, newcomer)
    put(
        world.businesses,
        business("Bakery", "2026-11-03", (newcomer, BusinessMemberRole.OWNER)),
    )

    world.clock.set("2026-11-04")

    assert tick(world) == 0
    assert "new@bakery.example" not in {
        str(item.contact.address) for item in world.notifier.sent
    }


def test_a_missed_notice_goes_out_late_until_the_grace_period_ends() -> None:
    late = NoticeWorld((*SUBPROCESSORS, ADDITION), today="2026-12-05")

    assert tick(late) == 2
    assert all(notice.is_late for notice in notices(late))
    english = next(
        str(item.text)
        for item in late.notifier.sent
        if str(item.contact.address) == "owner@cafe.example"
    )
    assert "should have told you earlier" in english
    assert "object" not in english

    too_late = NoticeWorld((*SUBPROCESSORS, ADDITION), today="2027-01-01")

    assert tick(too_late) == 0
    assert too_late.notifier.sent == []


def test_a_removal_is_announced_without_an_objection() -> None:
    retiring = retiring_entry(removed_on="2026-12-01", announced_on="2026-10-15")
    world = NoticeWorld((retiring, *SUBPROCESSORS[1:]), today="2026-11-01")

    assert tick(world) == 2
    english = next(
        str(item.text)
        for item in world.notifier.sent
        if str(item.contact.address) == "owner@cafe.example"
    )
    assert english.startswith("Sub-processor leaving on 2026-12-01: OpenAI")
    assert "no longer uses" in english and "object" not in english
    assert {notice.kind for notice in notices(world)} == {
        SubprocessorChangeKind.REMOVED
    }


def test_one_failing_business_keeps_the_announcement_open_for_it() -> None:
    world = NoticeWorld((*SUBPROCESSORS, ADDITION), today="2026-11-01")
    world.notifier.failing_business = world.salon.id

    assert tick(world) == 1
    (announcement,) = world.announcements.list_all()
    assert announcement.completed_at is None

    world.notifier.failing_business = None
    world.clock.set("2026-11-02")

    assert tick(world) == 1
    assert {notice.business_id for notice in notices(world)} == {
        world.salon.id,
        world.cafe.id,
    }
    (announcement,) = world.announcements.list_all()
    assert announcement.completed_at == moment("2026-11-02")
    assert int(announcement.notified_business_count) == 2


def test_a_business_whose_owners_have_no_address_is_recorded_once() -> None:
    world = NoticeWorld((*SUBPROCESSORS, ADDITION), today="2026-11-01")
    silent = user("en")
    put(world.users, silent)
    put(
        world.businesses,
        business("Kiosk", "2026-10-02", (silent, BusinessMemberRole.OWNER)),
    )

    assert tick(world) == 3

    kiosk = next(
        notice
        for notice in notices(world)
        if notice.business_id != world.salon.id and notice.business_id != world.cafe.id
    )
    assert int(kiosk.recipient_count) == 0
    assert len(world.notifier.sent) == 3
