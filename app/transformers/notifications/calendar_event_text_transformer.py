from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations.calendar_connection import CalendarEventText
from app.schemas.dto.operations.message_texts import CalendarEventTextInput
from app.schemas.typings.bookings.strings import (
    CalendarEventDescription,
    CalendarEventTitle,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.message_rendering import (
    CHANNEL_LABELS,
    NOTES_LINE,
    describe_phone,
    localized,
    render,
    resolve_label,
    text_or_missing,
)
from app.utilities.scheduling.localized_formatting import choose_template_language

EVENT_TITLE: LocalizedText = localized(
    en="Booking: {name}, guests: {party}",
    ru="Бронь: {name}, гостей: {party}",
    ka="ჯავშანი: {name}, სტუმრები: {party}",
)
EVENT_DESCRIPTION: LocalizedText = localized(
    en="{resource}\nPhone: {phone}\nChannel: {channel}\nBooking: {booking_id}",
    ru="{resource}\nТелефон: {phone}\nКанал: {channel}\nБронь: {booking_id}",
    ka="{resource}\nტელეფონი: {phone}\nარხი: {channel}\nჯავშანი: {booking_id}",
)


class CalendarEventTextTransformer(
    TransformerContract[CalendarEventTextInput, CalendarEventText]
):
    """Title and description of a booking's event in the owner's calendar."""

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: CalendarEventTextInput) -> CalendarEventText:
        language: LanguageTag = choose_template_language(
            EVENT_TITLE, input_data.language
        )
        booking = input_data.booking
        title: str = render(
            self._text_resolver,
            EVENT_TITLE,
            language,
            {
                "name": text_or_missing(booking.contact_name),
                "party": str(int(booking.party_size)),
            },
        )
        lines: list[str] = [
            render(
                self._text_resolver,
                EVENT_DESCRIPTION,
                language,
                {
                    "resource": str(booking.resource_name),
                    "phone": describe_phone(
                        input_data.contact_phone_display,
                        booking.contact_phone_number,
                    ),
                    "channel": resolve_label(
                        self._text_resolver,
                        CHANNEL_LABELS,
                        booking.source_channel,
                        language,
                    ),
                    "booking_id": str(booking.id),
                },
            )
        ]
        if booking.notes is not None:
            lines.append(
                render(
                    self._text_resolver,
                    NOTES_LINE,
                    language,
                    {"notes": str(booking.notes)},
                )
            )

        return CalendarEventText(
            title=CalendarEventTitle(title),
            description=CalendarEventDescription("\n".join(lines)),
        )
