"""
The texts of a waiting deposit's notices in the customer's language: the
reminder names the booking (or the banquet request), until when it holds,
the amount and the same link; the release names the booking that was let go.
"""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.deposits import DepositSubject
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositRequestDocument, DepositSettingsDocument
from app.schemas.dto.deposits.deposit_amounts import DepositAmount
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.deposits.payment_lines import PaymentLines
from app.utilities.deposits.deposit_reminder_texts import (
    DEPOSIT_BANQUET_REMINDER,
    DEPOSIT_BOOKING_RELEASED,
    DEPOSIT_BOOKING_REMINDER,
)
from app.utilities.deposits.deposit_times import hold_end_text
from app.utilities.scheduling.localized_formatting import (
    choose_template_language,
    format_full_date,
    isolate,
)
from app.utilities.scheduling.zoned_time import load_time_zone, to_local_moment


@dataclass(frozen=True)
class DepositNoticeTexts:
    lines: PaymentLines
    text_resolver: LocalizedTextResolverContract

    def reminder(
        self,
        business: BusinessDocument,
        settings: DepositSettingsDocument,
        request: DepositRequestDocument,
        booking: BookingDocument | None,
        now: Microseconds,
    ) -> MessageText | None:
        """None when the request's payment page is gone (nothing to remind of)."""

        link = next(
            (
                link
                for link in settings.payment_links
                if link.id == request.payment_link_id
            ),
            None,
        )
        if link is None:
            return None

        is_booking: bool = (
            request.subject is DepositSubject.BOOKING and booking is not None
        )
        template: LocalizedText = (
            DEPOSIT_BOOKING_REMINDER if is_booking else DEPOSIT_BANQUET_REMINDER
        )
        language: LanguageTag = choose_template_language(template, request.language)
        zone: ZoneInfo = load_time_zone(business.timezone)
        amount = DepositAmount(
            amount_minor=request.amount_minor, currency_code=request.currency_code
        )
        values: dict[str, str] = {
            "business": isolate(str(business.name), language),
            "until": str(hold_end_text(request.hold_expires_at, now, zone, language)),
            "amount": isolate(
                str(self.lines.amount_text(template, amount, language)), language
            ),
            "link": str(self.lines.url(link, amount, request.reference)),
            **booking_moment(booking, zone, language),
        }
        return self._render(template, language, values)

    def released(
        self,
        business: BusinessDocument,
        request: DepositRequestDocument,
        booking: BookingDocument,
    ) -> MessageText:
        language: LanguageTag = choose_template_language(
            DEPOSIT_BOOKING_RELEASED, request.language
        )
        values: dict[str, str] = {
            "business": isolate(str(business.name), language),
            **booking_moment(booking, load_time_zone(business.timezone), language),
        }
        return self._render(DEPOSIT_BOOKING_RELEASED, language, values)

    def _render(
        self, template: LocalizedText, language: LanguageTag, values: dict[str, str]
    ) -> MessageText:
        text: str = str(self.text_resolver.resolve(template, language))
        return MessageText(text.format(**values))


def booking_moment(
    booking: BookingDocument | None, zone: ZoneInfo, language: LanguageTag
) -> dict[str, str]:
    """The booking's local date and start time (none for a banquet request)."""

    if booking is None:
        return {}

    starts: datetime = to_local_moment(int(booking.starts_at), zone)
    return {
        "date": format_full_date(starts.date(), language),
        "time": isolate(starts.strftime("%H:%M"), language),
    }
