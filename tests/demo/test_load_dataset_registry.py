"""The bulk history of a load business: its size, its times and its seed."""

from collections import Counter

from typed_time_provider import Microseconds

from app.registries.billing.plan_registry import PlanRegistry
from app.registries.demo.demo_dataset_registry import DemoDatasetRegistry
from app.registries.demo.load.load_bookings import bookable_resources
from app.registries.demo.load_dataset_registry import LoadDatasetRegistry
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.demo_data import DemoFoundationRequest
from app.schemas.dto.load_data import (
    LoadBusinessShare,
    LoadVolume,
    LoadVolumeRequest,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.demo.constrained_integers import (
    LoadBookingCount,
    LoadMessageCount,
    LoadRandomSeed,
    LoadVisitorCount,
)
from app.schemas.typings.users.prefixed_id import UserId

NOW: int = 1_791_500_000_000_000
NOW_SECONDS: int = NOW // 1_000_000
UPCOMING: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CONFIRMED, BookingStatus.CANCELLED}
)
PAST: frozenset[BookingStatus] = frozenset(
    {BookingStatus.COMPLETED, BookingStatus.NO_SHOW, BookingStatus.CANCELLED}
)


def build_request(
    seed: int, messages: int = 1_003, visitors: int = 4
) -> LoadVolumeRequest:
    foundation = DemoDatasetRegistry(plan_registry=PlanRegistry()).build_foundations(
        DemoFoundationRequest(
            owner_id=UserId(), staff_id=UserId(), now=Microseconds(NOW)
        )
    )[0]
    return LoadVolumeRequest(
        business=foundation.business,
        resources=foundation.resources,
        channel_kinds=[
            ChannelKind.TELEGRAM,
            ChannelKind.WHATSAPP,
            ChannelKind.WEB_CHAT,
        ],
        assistant_version_id=AssistantVersionId(),
        model_id=LlmModelId("gpt-5-mini"),
        share=LoadBusinessShare(
            message_count=LoadMessageCount(messages),
            booking_count=LoadBookingCount(300),
            visitor_count=LoadVisitorCount(visitors),
        ),
        random_seed=LoadRandomSeed(seed),
        now=Microseconds(NOW),
    )


def test_the_history_has_the_requested_size_and_shape() -> None:
    request = build_request(seed=5)
    volume: LoadVolume = LoadDatasetRegistry().build_volume(request)
    sizes = Counter(str(message.conversation_id) for message in volume.messages)
    visitor_ids = {str(visitor.conversation_id) for visitor in volume.visitors}

    assert len(volume.messages) == 1_003
    assert len(volume.contacts) == len(volume.conversations) == 99 + 1 + 4
    assert sorted(sizes[key] for key in visitor_ids) == [2, 2, 2, 2]
    assert sorted(set(sizes.values())) == [2, 5, 10]
    assert all(int(message.created_at) <= NOW for message in volume.messages)
    assert all(
        int(conversation.last_message_at) <= NOW
        for conversation in volume.conversations
    )
    assistant = [m for m in volume.messages if m.author is MessageAuthor.ASSISTANT]
    assert all(int(message.cost_micro_usd) > 0 for message in assistant)
    for visitor in volume.visitors:
        latest = max(
            (
                m
                for m in volume.messages
                if m.conversation_id == visitor.conversation_id
            ),
            key=lambda m: int(m.created_at),
        )
        assert latest.id == visitor.latest_message_id
        assert len(str(visitor.session_key)) >= 16


def test_bookings_cover_the_past_and_the_next_two_months() -> None:
    request = build_request(seed=5)
    volume = LoadDatasetRegistry().build_volume(request)
    resource_ids = {resource.id for resource in bookable_resources(request.resources)}

    assert len(volume.bookings) == 300
    for booking in volume.bookings:
        assert booking.resource_id in resource_ids
        assert int(booking.ends_at) > int(booking.starts_at)
        if int(booking.starts_at) > NOW_SECONDS:
            assert booking.status in UPCOMING
            assert booking.reminder_sent_at is not None
        else:
            assert booking.status in PAST
            assert booking.reminder_sent_at is None
    assert min(int(b.starts_at) for b in volume.bookings) < NOW_SECONDS - 200 * 86_400
    assert max(int(b.starts_at) for b in volume.bookings) > NOW_SECONDS + 30 * 86_400


def test_the_same_seed_builds_the_same_shape() -> None:
    first = LoadDatasetRegistry().build_volume(build_request(seed=9))
    again = LoadDatasetRegistry().build_volume(build_request(seed=9))
    other = LoadDatasetRegistry().build_volume(build_request(seed=10))

    def shape(volume: LoadVolume) -> list[tuple[int, str]]:
        return [(int(m.created_at), str(m.text)) for m in volume.messages]

    assert shape(first) == shape(again)
    assert shape(first) != shape(other)


def test_too_few_messages_leave_out_visitors() -> None:
    volume = LoadDatasetRegistry().build_volume(
        build_request(seed=1, messages=5, visitors=4)
    )

    assert len(volume.visitors) == 2
    assert len(volume.messages) == 5
