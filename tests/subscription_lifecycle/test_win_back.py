"""Owners who cancelled hear from us on day 14 and day 30, once each."""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    SubscriptionEventKind,
    WinBackStage,
)
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from app.schemas.dto.subscription_lifecycle import CancelSubscriptionRequest
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.grace_steps import pay_open_invoices
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld

DAY_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000


def cancelled_business(
    world: LifecycleWorld,
    reason: CancellationReason | None = CancellationReason.SEASONAL_BREAK,
) -> tuple[UserDocument, BusinessDocument, Microseconds]:
    """A paying business with a Telegram chat on the bot, cancelled now."""

    owner, business = world.paying_business()
    stored = world.business(business.id)
    stored.manager_contacts.append(
        ManagerContact(
            name=ManagerName("Front desk"),
            channel=ManagerContactChannel.TELEGRAM,
            address=ManagerContactAddress("123456789"),
            language=LanguageTag("ru"),
        )
    )
    world.business_repo.save(stored)
    world.cancel_subscription.run(
        CancelSubscriptionCommand(
            user_id=owner.id,
            business_id=business.id,
            request=CancelSubscriptionRequest(reason=reason),
        )
    )
    return owner, stored, world.clock.now()


def at_day(world: LifecycleWorld, cancelled_at: Microseconds, days: float) -> None:
    world.clock.move_to(Microseconds(int(cancelled_at) + int(days * DAY_MICROSECONDS)))


def customer_writes(world: LifecycleWorld, business: BusinessDocument) -> None:
    moment = world.clock.now()
    world.conversation_repo.save(
        ConversationDocument(
            business_id=business.id,
            contact_id=ContactId(),
            assistant_version_id=AssistantVersionId(),
            channel=ChannelKind.TELEGRAM,
            channel_user_id=ChannelUserId("tg-777"),
            last_message_at=moment,
            created_at=moment,
            updated_at=moment,
        )
    )


def win_back_steps(world: LifecycleWorld, business: BusinessDocument) -> list[object]:
    return [
        step.win_back_stage
        for step in world.steps(business)
        if step.kind is SubscriptionEventKind.WIN_BACK_SENT
    ]


def test_day_14_tells_the_owner_what_the_assistant_did_since() -> None:
    world = LifecycleWorld()
    _, business, cancelled_at = cancelled_business(world)
    at_day(world, cancelled_at, 3)
    customer_writes(world, business)
    customer_writes(world, business)
    world.notifier.sent.clear()

    at_day(world, cancelled_at, 13.9)
    assert world.run_win_back_job() == 0
    at_day(world, cancelled_at, 14)
    assert world.run_win_back_job() == 1

    recipients = [contact.channel for contact, _ in world.notifier.sent]
    assert sorted(channel.value for channel in recipients) == ["email", "telegram"]
    telegram = next(
        str(text)
        for contact, text in world.notifier.sent
        if contact.channel is ManagerContactChannel.TELEGRAM
    )
    assert "ассистент всё ещё на месте" in telegram
    assert "Клиентов, написавших за это время: 2." in telegram
    assert "/n/" in telegram  # a signed link to Billing
    email = next(
        str(text)
        for contact, text in world.notifier.sent
        if contact.channel is ManagerContactChannel.EMAIL
    )
    assert "your assistant is still here" in email
    # A stage goes out once.
    assert world.run_win_back_job() == 0
    assert win_back_steps(world, business) == [WinBackStage.DAY_14]


def test_day_30_adds_a_hint_for_the_reason_given() -> None:
    world = LifecycleWorld()
    _, business, cancelled_at = cancelled_business(world)
    at_day(world, cancelled_at, 14)
    world.run_win_back_job()
    world.notifier.sent.clear()

    at_day(world, cancelled_at, 30)
    assert world.run_win_back_job() == 1

    email = str(world.notifier.sent[-1][1])
    assert "a month without full service" in email
    assert "pause for a share of the price" in email
    assert win_back_steps(world, business) == [WinBackStage.DAY_14, WinBackStage.DAY_30]


def test_a_job_that_was_down_sends_only_the_latest_stage() -> None:
    world = LifecycleWorld()
    _, business, cancelled_at = cancelled_business(world, reason=None)

    at_day(world, cancelled_at, 31)
    assert world.run_win_back_job() == 1

    assert win_back_steps(world, business) == [WinBackStage.DAY_30]
    at_day(world, cancelled_at, 46)
    assert world.run_win_back_job() == 0


def test_an_owner_who_came_back_hears_nothing() -> None:
    world = LifecycleWorld()
    owner, business, cancelled_at = cancelled_business(world)
    at_day(world, cancelled_at, 5)
    pay_open_invoices(world, owner, business, payment_id=5)

    at_day(world, cancelled_at, 14)
    assert world.run_win_back_job() == 0
    assert win_back_steps(world, business) == []


def test_messages_wait_for_the_businesss_daytime() -> None:
    world = LifecycleWorld()
    _, _, cancelled_at = cancelled_business(world)
    # The cancellation was at 13:00 in Tbilisi; ten hours later it is night.
    at_day(world, cancelled_at, 14 + 10 / 24)
    assert world.run_win_back_job() == 0

    at_day(world, cancelled_at, 15)
    assert world.run_win_back_job() == 1
