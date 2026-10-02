"""Everything needed to place one booking on a local date."""

from collections.abc import Sequence
from datetime import date
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.profiles import BookingRules, OpeningInterval
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.typings.bookings.constrained_integers import BookingDurationMinutes
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.utilities.scheduling.nights import StayTimes


class PlacementRequest(NamedTuple):
    """Everything needed to place one booking on a local date."""

    local_date: date
    minute_of_day: int | None
    duration_minutes: BookingDurationMinutes | None
    nights: int | None
    zone: ZoneInfo
    business_hours: Sequence[OpeningInterval]
    exceptions: Sequence[ScheduleExceptionDocument]
    bookings: Sequence[BookingDocument]
    rules: BookingRules | None
    stay_times: StayTimes
    earliest_start: int
    include_sandbox: bool
    excluded_booking_id: BookingId | None = None
