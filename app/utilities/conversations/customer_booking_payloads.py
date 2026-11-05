"""The list_my_bookings result as the language model reads it."""

from app.schemas.dto.bookings import BookingView
from app.schemas.dto.customer_bookings import CustomerBookingList
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.utilities.conversations.offer_payloads import major_units
from app.utilities.conversations.tool_payloads import render, with_business_today

NO_BOOKINGS_NOTE: str = (
    "No bookings still to come were found for this customer. Only bookings "
    "made in this conversation or under the number the customer writes or "
    "calls from can be looked up; for another number offer to pass the "
    "question to a colleague."
)


def render_customer_bookings(
    result: CustomerBookingList,
    business_today: str | None = None,
) -> LlmToolResultJson:
    """`{"bookings": [...], "business_today": ...}`, the soonest first."""

    payload: dict[str, object] = {
        "bookings": [render_listed_booking(booking) for booking in result.bookings]
    }
    if not result.bookings:
        payload["note"] = NO_BOOKINGS_NOTE

    return render(with_business_today(payload, business_today))


def render_listed_booking(booking: BookingView) -> dict[str, object]:
    rendered: dict[str, object] = {
        "booking_id": str(booking.id),
        "status": booking.status.value,
        "resource_name": str(booking.resource_name),
        "date": str(booking.date),
        "end_date": str(booking.end_date),
        "party_size": int(booking.party_size),
        "timezone": str(booking.timezone),
    }
    if booking.time is not None:
        rendered["time"] = str(booking.time)

    if booking.end_time is not None:
        rendered["end_time"] = str(booking.end_time)

    if booking.service_title is not None:
        rendered["service"] = str(booking.service_title)

    if booking.value_minor is not None and booking.currency_code is not None:
        rendered["price"] = major_units(int(booking.value_minor), booking.currency_code)
        rendered["currency"] = str(booking.currency_code)

    return rendered
