"""
The bookings of a load business: made by its chat customers for its
active resources, from ten months ago to two months ahead, at whole or
half hours of the day (06:00 to 17:30 UTC: business hours in Europe and
the Caucasus). Past ones mostly happened; upcoming ones are mostly
confirmed, their reminders already sent so a load run does not start
with a burst of reminder messages.
"""

import random

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.load_data import LoadVolumeRequest
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)

DAY_SECONDS: int = 86_400
HALF_HOUR_SECONDS: int = 1_800
PAST_DAYS: int = 300
FUTURE_DAYS: int = 60
FIRST_SLOT: int = 12  # 06:00 UTC, in half hours
LAST_SLOT: int = 36  # 18:00 UTC, exclusive
BOOKED_AHEAD_SECONDS: int = 2 * DAY_SECONDS
PAST_STATUS_WEIGHTS: dict[BookingStatus, int] = {
    BookingStatus.COMPLETED: 80,
    BookingStatus.CANCELLED: 15,
    BookingStatus.NO_SHOW: 5,
}
UPCOMING_STATUS_WEIGHTS: dict[BookingStatus, int] = {
    BookingStatus.CONFIRMED: 90,
    BookingStatus.CANCELLED: 10,
}


def bookable_resources(resources: list[ResourceDocument]) -> list[ResourceDocument]:
    """Active resources booked by time slot (else any active resource)."""

    active: list[ResourceDocument] = [
        resource for resource in resources if resource.is_active
    ]
    by_slot: list[ResourceDocument] = [
        resource
        for resource in active
        if resource.booking_unit is BookingUnit.TIME_SLOT
    ]
    return by_slot or active


def build_bookings(
    request: LoadVolumeRequest,
    conversations: list[ConversationDocument],
    chooser: random.Random,
) -> list[BookingDocument]:
    resources: list[ResourceDocument] = bookable_resources(request.resources)
    chats: list[ConversationDocument] = [
        conversation for conversation in conversations if not conversation.is_sandbox
    ]
    if not resources or not chats:
        return []

    now_seconds: int = int(request.now) // 1_000_000
    today: int = now_seconds - now_seconds % DAY_SECONDS
    return [
        build_booking(
            request,
            chooser.choice(resources),
            chooser.choice(chats),
            today,
            now_seconds,
            chooser,
        )
        for _ in range(int(request.share.booking_count))
    ]


def build_booking(
    request: LoadVolumeRequest,
    resource: ResourceDocument,
    conversation: ConversationDocument,
    today: int,
    now_seconds: int,
    chooser: random.Random,
) -> BookingDocument:
    day: int = chooser.randrange(-PAST_DAYS, FUTURE_DAYS)
    starts_at: int = (
        today
        + day * DAY_SECONDS
        + chooser.randrange(FIRST_SLOT, LAST_SLOT) * HALF_HOUR_SECONDS
    )
    minutes: int = (
        int(resource.slot_minutes)
        if resource.slot_minutes is not None
        else chooser.choice((60, 90, 120))
    )
    is_upcoming: bool = starts_at > now_seconds
    weights = UPCOMING_STATUS_WEIGHTS if is_upcoming else PAST_STATUS_WEIGHTS
    status: BookingStatus = chooser.choices(list(weights), list(weights.values()))[0]
    made_at = Microseconds(
        max(0, min(starts_at - BOOKED_AHEAD_SECONDS, now_seconds - 3_600)) * 1_000_000
    )
    return BookingDocument(
        business_id=request.business.id,
        resource_id=resource.id,
        contact_id=conversation.contact_id,
        conversation_id=conversation.id,
        starts_at=BookingStartsAtUnixSeconds(starts_at),
        ends_at=BookingEndsAtUnixSeconds(starts_at + minutes * 60),
        party_size=PartySize(
            max(1, min(int(resource.capacity), chooser.randint(1, 4)))
        ),
        status=status,
        source_channel=conversation.channel,
        reminder_sent_at=made_at if is_upcoming else None,
        language=conversation.language,
        created_at=made_at,
        updated_at=made_at,
    )
