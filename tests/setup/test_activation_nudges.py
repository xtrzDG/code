"""The activation nudges job: once per business and nudge, never after an opt-out."""

from typed_time_provider import Microseconds

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.nudges import NudgeCode
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.domain.setup import ActivationEventDocument, SetupStateDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.setup.send_activation_nudges_use_case import (
    SendActivationNudgesUseCase,
)
from app.utilities.setup.setup_keys import derive_activation_event_id
from tests.setup.guide_world import GuideWorld


def nudge_job(world: GuideWorld) -> SendActivationNudgesUseCase:
    """A fresh job over the world's stores (a worker after a restart)."""

    return SendActivationNudgesUseCase(
        business_repo=world.businesses,
        channel_repo=world.channels,
        activation_event_repo=world.events,
        setup_state_repo=world.states,
        nudge_sent_repo=world.nudges_sent,
        owner_nudges=world.nudges,
        wall_clock=world.clock.wall_clock,
    )


def run(world: GuideWorld) -> int:
    tick = JobTick(job_name=JobName("send_activation_nudges"), scheduled_at=world.now())
    return int(nudge_job(world).run(tick).processed_count)


def sent_codes(world: GuideWorld) -> set[NudgeCode]:
    return {
        code
        for code in NudgeCode
        if world.nudges_sent.find(world.business.id, code) is not None
    }


def go_live(world: GuideWorld) -> None:
    now: Microseconds = world.now()
    world.events.record_once(
        ActivationEventDocument(
            id=derive_activation_event_id(
                world.business.id, ActivationEventKind.WENT_LIVE
            ),
            business_id=world.business.id,
            kind=ActivationEventKind.WENT_LIVE,
            occurred_at=now,
        )
    )
    world.business = world.business.model_copy(
        update={
            "status": BusinessStatus.LIVE,
            "published_assistant_version_id": AssistantVersionId(),
        }
    )
    world.businesses.save(world.business)


def test_day_1_reaches_the_owner_once_by_email_telegram_and_device() -> None:
    world = GuideWorld()
    world.add_device(world.owner, "ka")
    world.advance(days=1)

    assert run(world) == 1
    assert sent_codes(world) == {NudgeCode.NOT_LIVE_DAY_1}
    channels = sorted(contact.channel.value for contact, _ in world.notifier.sent)
    assert channels == ["email", "telegram"]
    email = next(
        text
        for contact, text in world.notifier.sent
        if contact.channel is ManagerContactChannel.EMAIL
    )
    assert str(email).startswith("Salobie Bia: помощник почти готов")
    assert "Настройки → Уведомления" in str(email)
    [push] = world.push_queue.queued
    assert str(push.brief.title) == "Salobie Bia: ასისტენტი თითქმის მზადაა"
    assert str(push.subject) == "nudge:not_live_day_1"
    nudge = world.nudges_sent.find(world.business.id, NudgeCode.NOT_LIVE_DAY_1)
    assert nudge is not None
    assert int(nudge.recipient_count) == 3


def test_a_restarted_worker_sends_nothing_twice() -> None:
    world = GuideWorld()
    world.advance(days=1)
    run(world)
    first = len(world.notifier.sent)

    world.advance(hours=1)
    assert run(world) == 0
    world.advance(hours=1)
    assert run(world) == 0
    assert len(world.notifier.sent) == first

    world.advance(days=2)
    assert run(world) == 1
    assert sent_codes(world) == {NudgeCode.NOT_LIVE_DAY_1, NudgeCode.NOT_LIVE_DAY_3}


def test_owners_who_turned_reminders_off_hear_nothing() -> None:
    world = GuideWorld()

    def turn_off(state: SetupStateDocument) -> None:
        state.reminders_off_at = world.now()

    world.states.change(world.business.id, turn_off, world.now())
    world.advance(days=1)

    assert run(world) == 0
    assert world.notifier.sent == []
    assert sent_codes(world) == set()


def test_after_going_live_the_nudges_ask_for_customers() -> None:
    world = GuideWorld()
    world.connect(ChannelKind.WEB_CHAT)
    go_live(world)
    world.advance(days=2)

    assert run(world) == 1
    assert sent_codes(world) == {NudgeCode.LIVE_DAY_2}
    # No customer has written yet: the link comes first.
    email = next(
        text
        for contact, text in world.notifier.sent
        if contact.channel is ManagerContactChannel.EMAIL
    )
    assert "Поделитесь ссылкой на чат" in str(email)

    world.connect(ChannelKind.TELEGRAM)

    def shared(state: SetupStateDocument) -> None:
        state.hosted_page_visited_at = world.now()

    world.states.change(world.business.id, shared, world.now())
    world.advance(days=8)
    assert run(world) == 0
    assert NudgeCode.LIVE_DAY_10 not in sent_codes(world)


def test_businesses_older_than_the_schedule_and_paused_ones_are_left_alone() -> None:
    world = GuideWorld()
    world.advance(days=40)
    assert run(world) == 0

    paused = GuideWorld()
    go_live(paused)
    paused.business = paused.business.model_copy(
        update={"status": BusinessStatus.PAUSED}
    )
    paused.businesses.save(paused.business)
    paused.advance(days=2)
    assert run(paused) == 0
