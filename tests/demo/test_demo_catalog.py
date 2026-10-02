"""
The demo catalog is built relative to the moment of seeding, so it must
hold together whenever a developer starts the API: any hour, any weekday,
daylight saving days included.
"""

from datetime import UTC, datetime, timedelta

import pytest
from typed_time_provider import Microseconds

from app.registries.billing.plan_registry import PlanRegistry
from app.registries.demo.demo_dataset_registry import DemoDatasetRegistry
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.demo_data import (
    DemoActivityRequest,
    DemoBusinessActivity,
    DemoFoundationRequest,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.users.prefixed_id import UserId

MICROSECONDS_PER_SECOND: int = 1_000_000
# Every 5 hours over a week (each hour of the day on some weekday), plus
# the nights the clocks change in Berlin.
MOMENTS: list[datetime] = [
    datetime(2026, 10, 5, 0, 17, tzinfo=UTC) + timedelta(hours=5 * step)
    for step in range(34)
] + [
    datetime(2026, 10, 25, 1, 30, tzinfo=UTC),
    datetime(2027, 3, 28, 1, 30, tzinfo=UTC),
]
MESSENGERS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.TELEGRAM, ChannelKind.WHATSAPP, ChannelKind.INSTAGRAM}
)
REMINDER_LEAD_SECONDS: int = 24 * 60 * 60
UPCOMING_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CONFIRMED, BookingStatus.CANCELLED}
)
PAST_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.COMPLETED, BookingStatus.NO_SHOW, BookingStatus.CANCELLED}
)


def build_demo(moment: datetime) -> list[DemoBusinessActivity]:
    now = Microseconds(int(moment.timestamp()) * MICROSECONDS_PER_SECOND)
    registry = DemoDatasetRegistry(PlanRegistry())
    foundations = registry.build_foundations(
        DemoFoundationRequest(owner_id=UserId(), staff_id=UserId(), now=now)
    )
    return [
        registry.build_activity(
            DemoActivityRequest(
                foundation=foundation,
                version_ids=[
                    AssistantVersionId() for _ in foundation.assistant_versions
                ],
                model_id=LlmModelId("gpt-5-mini"),
                now=now,
            )
        )
        for foundation in foundations
    ]


@pytest.mark.parametrize("moment", MOMENTS, ids=lambda moment: moment.isoformat())
def test_the_story_holds_together_at_any_moment(moment: datetime) -> None:
    now_seconds: int = int(moment.timestamp())
    for activity in build_demo(moment):
        contacts = {contact.id: contact for contact in activity.contacts}
        assert all(
            int(message.created_at) <= now_seconds * MICROSECONDS_PER_SECOND
            for message in activity.messages
        )
        for booking in activity.bookings:
            if int(booking.starts_at) > now_seconds:
                assert booking.status in UPCOMING_STATUSES
            else:
                assert booking.status in PAST_STATUSES
            in_messenger: bool = any(
                identity.channel in MESSENGERS
                for identity in contacts[booking.contact_id].channel_identities
            )
            if booking.status is BookingStatus.CONFIRMED and in_messenger:
                # The reminder job would write to the made-up credentials.
                assert int(booking.starts_at) - now_seconds <= REMINDER_LEAD_SECONDS
                assert booking.reminder_sent_at is not None


def test_the_restaurant_covers_what_the_cabinet_shows() -> None:
    restaurant, salon = build_demo(datetime(2026, 10, 2, 9, 0, tzinfo=UTC))

    real = [c for c in restaurant.conversations if not c.is_sandbox]
    assert 38 <= len(real) <= 45
    assert {c.language for c in real} == {"ka", "ru", "en", "he", "ar"}
    assert {c.channel for c in real} == {
        ChannelKind.TELEGRAM,
        ChannelKind.WHATSAPP,
        ChannelKind.WEB_CHAT,
        ChannelKind.PHONE,
    }
    assert {b.status for b in restaurant.bookings} == set(BookingStatus) - {
        BookingStatus.PENDING
    }
    assert any(message.tool_calls for message in restaurant.messages)
    assert len(restaurant.calls) == 1
    assert restaurant.autotest_run.is_passed
    assert {h.status.value for h in restaurant.handoffs} == {"notified", "resolved"}
    assert salon.subscription.currency_code == "EUR"


def test_exactly_one_version_of_each_business_is_published() -> None:
    registry = DemoDatasetRegistry(PlanRegistry())
    foundations = registry.build_foundations(
        DemoFoundationRequest(
            owner_id=UserId(),
            staff_id=UserId(),
            now=Microseconds(1_790_000_000_000_000),
        )
    )

    for foundation in foundations:
        statuses = [plan.status for plan in foundation.assistant_versions]
        assert statuses.count(AssistantVersionStatus.PUBLISHED) == 1
