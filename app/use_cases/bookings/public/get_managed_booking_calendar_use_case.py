from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.booking_manage import (
    BookingCalendarEvent,
    BookingCalendarFile,
    ManagedBookingAction,
    ManagedBookingView,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.bookings.strings import (
    CalendarEventDescription,
    CalendarEventTitle,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.use_cases.bookings.guest_booking import GuestBooking
from app.use_cases.bookings.public.managed_booking_pages import ManagedBookingPages
from app.utilities.bookings.booking_calendar_files import (
    calendar_file_name,
    render_calendar_file,
)
from app.utilities.bookings.booking_confirmation_texts import (
    GUESTS_LINE,
    MANAGE_LINE,
    SERVICE_LINE,
)
from app.utilities.bookings.booking_manage_links import build_manage_link
from app.utilities.bookings.manage_rate_limits import MANAGE_VIEW_LIMITS


class GetManagedBookingCalendarUseCase(
    UseCaseContract[ManagedBookingAction, BookingCalendarFile]
):
    """
    The booking as an .ics file for the guest's calendar: the business and
    service as its title, the times in UTC, the address as its place and,
    in the guest's language, the party and the manage link. A cancelled
    booking's file says so (STATUS:CANCELLED), so a re-import removes it.
    """

    def __init__(
        self,
        pages: ManagedBookingPages,
        text_resolver: LocalizedTextResolverContract,
        cabinet_base_url: CabinetBaseUrl | None,
    ) -> None:
        self._pages: ManagedBookingPages = pages
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url

    def run(self, input_data: ManagedBookingAction) -> BookingCalendarFile:
        self._pages.refuse_too_frequent(input_data, MANAGE_VIEW_LIMITS)
        guest_booking: GuestBooking = self._pages.current(input_data.claims)
        booking: BookingDocument = guest_booking.booking
        view: ManagedBookingView = self._pages.view(
            guest_booking, self._pages.token_for(booking)
        )
        link = build_manage_link(self._cabinet_base_url, view.token)
        title: str = str(view.business_name)
        lines: list[str] = []
        if view.service_title is not None:
            title = f"{title} — {view.service_title}"
            lines.append(self._line(SERVICE_LINE, view, service=view.service_title))
        if int(view.party_size) > 1:
            lines.append(self._line(GUESTS_LINE, view, party_size=int(view.party_size)))
        if link is not None:
            lines.append(self._line(MANAGE_LINE, view, url=link))
        return BookingCalendarFile(
            file_name=calendar_file_name(view.date),
            content=render_calendar_file(
                BookingCalendarEvent(
                    booking_id=booking.id,
                    starts_at=booking.starts_at,
                    ends_at=booking.ends_at,
                    stamped_at=self._pages.wall_clock.now_unix(),
                    changed_at=booking.updated_at,
                    title=CalendarEventTitle(title),
                    description=CalendarEventDescription("\n".join(lines)),
                    location=view.address,
                    url=link,
                    status=booking.status,
                )
            ),
        )

    def _line(
        self, text: LocalizedText, view: ManagedBookingView, **values: object
    ) -> str:
        return str(self._text_resolver.resolve(text, view.language)).format(**values)
