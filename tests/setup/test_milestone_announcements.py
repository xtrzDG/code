"""A milestone's push: the team hears about it once, and never about old news."""

from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.setup import ActivationEventKind
from app.use_cases.setup.milestone_announcements import (
    ANNOUNCE_WITHIN_MICROSECONDS,
    announce_milestone,
)
from tests.operations.fakes import FakeLocalizedTextResolver
from tests.setup.guide_world import GuideWorld


def announce(world: GuideWorld, kind: ActivationEventKind, age: int = 0) -> None:
    now: Microseconds = world.now()
    announce_milestone(
        world.alerts,
        FakeLocalizedTextResolver(),
        world.business,
        kind,
        Microseconds(int(now) - age),
        now,
    )


def test_the_first_booking_reaches_the_teams_devices_and_telegram_chats() -> None:
    world = GuideWorld()
    world.add_device(world.owner, "ru")
    world.add_device(world.staff, "en")

    announce(world, ActivationEventKind.FIRST_BOOKING)

    # Telegram contacts get the detailed text; e-mail and SMS contacts none.
    [(contact, text)] = world.notifier.sent
    assert contact.channel is ManagerContactChannel.TELEGRAM
    assert "Salobie Bia" in str(text)
    assert "ჯავშანი" in str(text)  # Nino reads Georgian
    pushes = {str(push.brief.title) for push in world.push_queue.queued}
    assert pushes == {
        "Первая бронь, которую сделал помощник",
        "The first booking made by your assistant",
    }
    assert {str(push.subject) for push in world.push_queue.queued} == {
        "milestone:first_booking"
    }
    assert all(
        str(push.link).startswith("https://") for push in world.push_queue.queued
    )


def test_every_device_hears_a_milestone_whatever_events_it_chose() -> None:
    world = GuideWorld()
    world.add_device(world.owner, "ka")
    stored = world.preferences.get(world.business.id, world.owner)
    assert stored is None

    announce(world, ActivationEventKind.FIRST_AFTER_HOURS_BOOKING)

    [push] = world.push_queue.queued
    assert str(push.brief.title) == "ჯავშანი, როცა დაკეტილი იყავით"


def test_old_milestones_and_kinds_without_a_celebration_are_not_announced() -> None:
    world = GuideWorld()
    world.add_device(world.owner, "en")

    announce(
        world,
        ActivationEventKind.FIRST_CONVERSATION,
        age=ANNOUNCE_WITHIN_MICROSECONDS + 1,
    )
    announce(world, ActivationEventKind.WENT_LIVE)
    announce(world, ActivationEventKind.FIRST_HANDOFF)

    assert world.push_queue.queued == []
    assert world.notifier.sent == []
