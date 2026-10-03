"""Counts of business activity the database computes (dashboard, admin)."""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import model_validator
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.typings.conversations.booleans import IsAfterHours
from app.schemas.typings.insights.constrained_integers import (
    PeriodItemCount,
    TimelineSegment,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class ActivityPeriod(ImmutableDTO):
    """
    Activity that started from `start` (inclusive) to `end` (exclusive),
    counted per timeline segment: segment i runs from `segment_starts[i]` to
    the next start (the last one to `end`). The first start is `start`.
    """

    start: Microseconds
    end: Microseconds
    segment_starts: tuple[Microseconds, ...]

    @model_validator(mode="after")
    def require_segments_in_period(self) -> Self:
        starts: list[int] = [int(start) for start in self.segment_starts]
        if not starts or starts[0] != int(self.start):
            raise ValueError("The first segment starts with the period.")

        if starts != sorted(set(starts)) or starts[-1] >= int(self.end):
            raise ValueError("Segment starts ascend inside the period.")

        return self


class BookingActivityCount(ImmutableDTO):
    """Bookings made in one timeline segment with one status."""

    status: BookingStatus
    segment: TimelineSegment
    count: PeriodItemCount


class HandoffActivityCount(ImmutableDTO):
    """Handoffs made in one timeline segment for one reason and urgency."""

    reason: HandoffReason
    urgency: HandoffUrgency
    segment: TimelineSegment
    count: PeriodItemCount


class ConversationMixCount(ImmutableDTO):
    """Conversations started in a period in one channel and language."""

    channel: ChannelKind
    language: LanguageTag | None = None
    count: PeriodItemCount


class ConversationTimelineCount(ImmutableDTO):
    """Conversations started in one timeline segment, flagged after hours or not."""

    is_after_hours: IsAfterHours
    segment: TimelineSegment
    count: PeriodItemCount
