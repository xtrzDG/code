"""
Localized templates of the brief staff alerts (e-mail, SMS, devices) and of
the link line every staff notification ends with. Brief texts say what
happened and where, never who the customer is.
"""

from collections.abc import Mapping

from app.schemas.constants.notifications import StaffBookingChange
from app.schemas.dto.localization import LocalizedText
from app.transformers.notifications.message_rendering import localized

HANDOFF_TITLE: LocalizedText = localized(
    en="A customer needs a person",
    ru="Клиенту нужен человек",
    ka="კლიენტს ადამიანი სჭირდება",
)
URGENT_HANDOFF_TITLE: LocalizedText = localized(
    en="Urgent: a customer needs a person",
    ru="Срочно: клиенту нужен человек",
    ka="სასწრაფო: კლიენტს ადამიანი სჭირდება",
)
HANDOFF_DETAIL: LocalizedText = localized(
    en="{business} · {reason}",
    ru="{business} · {reason}",
    ka="{business} · {reason}",
)
LEAD_TITLE: LocalizedText = localized(
    en="New request · {business}",
    ru="Новая заявка · {business}",
    ka="ახალი მოთხოვნა · {business}",
)
LEAD_DETAIL_WITH_DATE: LocalizedText = localized(
    en="{lead_type} · {date}",
    ru="{lead_type} · {date}",
    ka="{lead_type} · {date}",
)
BOOKING_TITLES: Mapping[StaffBookingChange, LocalizedText] = {
    StaffBookingChange.CREATED: localized(
        en="New booking · {business}",
        ru="Новая бронь · {business}",
        ka="ახალი ჯავშანი · {business}",
    ),
    StaffBookingChange.MOVED: localized(
        en="Booking moved · {business}",
        ru="Бронь перенесена · {business}",
        ka="ჯავშანი გადატანილია · {business}",
    ),
    StaffBookingChange.CANCELLED: localized(
        en="Booking cancelled · {business}",
        ru="Бронь отменена · {business}",
        ka="ჯავშანი გაუქმდა · {business}",
    ),
}
BOOKING_DETAIL: LocalizedText = localized(
    en="{period} · guests: {party}",
    ru="{period} · гостей: {party}",
    ka="{period} · სტუმრები: {party}",
)
LINK_LINE: LocalizedText = localized(
    en="Open: {link}",
    ru="Открыть: {link}",
    ka="გახსნა: {link}",
)
TEST_TITLE: LocalizedText = localized(
    en="Test notification · {business}",
    ru="Проверка уведомлений · {business}",
    ka="სატესტო შეტყობინება · {business}",
)
TEST_DETAIL: LocalizedText = localized(
    en="Handoffs, requests and bookings will arrive here.",
    ru="Сюда будут приходить передачи, заявки и брони.",
    ka="აქ მოვა გადამისამართებები, მოთხოვნები და ჯავშნები.",
)
