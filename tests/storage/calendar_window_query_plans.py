"""
The two reads of a bookings calendar window (Bookings → Day, Week, Nights)
and the index each must use: bookings starting in the window, and those
carried into it from before, both bounded on each side.
"""

from app.schemas.dto.booking_grid import BookingWindow
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.use_cases.bookings.calendar.grid_window import LONGEST_BOOKING_SECONDS
from tests.storage.list_query_plans import BUSINESS, FIRST_PAGE, ListQuery

# A week in the middle of the seeded bookings (starts 1_790_000_000 onwards).
WEEK_START: int = 1_800_000_000
WEEK_END: int = WEEK_START + 7 * 86_400

CALENDAR_WINDOW_QUERIES: tuple[ListQuery, ...] = (
    ListQuery(
        "calendar: bookings starting in a week",
        lambda r: r.bookings.page_in_window(
            BUSINESS,
            BookingWindow(
                starts_from=BookingSearchBoundSeconds(WEEK_START),
                starts_before=BookingSearchBoundSeconds(WEEK_END),
                ends_after=BookingSearchBoundSeconds(WEEK_START),
            ),
            FIRST_PAGE,
        ),
        "bookings",
        "bookings_doc_starts_at_idx",
        ("bookings_doc_ends_at_idx",),
    ),
    ListQuery(
        "calendar: bookings carried into a week",
        lambda r: r.bookings.page_in_window(
            BUSINESS,
            BookingWindow(
                starts_from=BookingSearchBoundSeconds(
                    WEEK_START - LONGEST_BOOKING_SECONDS
                ),
                starts_before=BookingSearchBoundSeconds(WEEK_START),
                ends_after=BookingSearchBoundSeconds(WEEK_START),
                ends_by=BookingSearchBoundSeconds(WEEK_START + LONGEST_BOOKING_SECONDS),
                include_sandbox=True,
            ),
            FIRST_PAGE,
        ),
        "bookings",
        "bookings_doc_starts_at_idx",
        ("bookings_doc_ends_at_idx", "bookings_doc_status_starts_at_idx"),
    ),
)
