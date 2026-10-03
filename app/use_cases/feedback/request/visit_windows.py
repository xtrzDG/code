"""Which businesses ask, and which of their visits are due a question now."""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.feedback import ReviewSettingsDocument
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds

MICROSECONDS_PER_SECOND: int = 1_000_000
SECONDS_PER_MINUTE: int = 60
# A question about a visit that became due hours ago (the worker was down)
# is not asked: "how was your visit?" days later reads as spam.
MAX_LATENESS: timedelta = timedelta(hours=6)
VISITED_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
)


def asks_for_feedback(
    business: BusinessDocument, settings: ReviewSettingsDocument
) -> bool:
    """Feedback on, and the assistant live (it answers the replies)."""

    return settings.is_feedback_enabled and business.status is BusinessStatus.LIVE


def due_visits_window(
    settings: ReviewSettingsDocument,
    now: Microseconds,
) -> tuple[BookingSearchBoundSeconds, BookingSearchBoundSeconds]:
    """
    The end times of the visits due a question now: ended at least
    `delay_minutes` ago, and at most the delay plus six hours ago.
    """

    now_seconds: int = int(now) // MICROSECONDS_PER_SECOND
    due_by: int = now_seconds - int(settings.delay_minutes) * SECONDS_PER_MINUTE
    earliest: int = due_by - int(MAX_LATENESS.total_seconds())
    return (
        BookingSearchBoundSeconds(max(earliest, 0)),
        BookingSearchBoundSeconds(max(due_by, 0)),
    )


def is_visit_to_ask_about(booking: BookingDocument) -> bool:
    """A real visit: completed, or still confirmed after it ended."""

    return booking.status in VISITED_STATUSES and not booking.is_sandbox
