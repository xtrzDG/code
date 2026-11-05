"""
The text of a guest's booking confirmation and the body parameters of its
WhatsApp template: the business, the local date and time (a stay's arrival
and departure), the party, the service, the address with a map link and
the manage link, in the guest's language.
"""

from dataclasses import dataclass

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.bookings import BookingConfirmationChange, BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessAddress
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.bookings.constrained_strings import BookingManageLink
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.bookings.booking_confirmation_texts import (
    ADDRESS_LINE,
    ARRIVAL_LINE,
    CONFIRMED_HEADLINE,
    DEPARTURE_LINE,
    GUESTS_LINE,
    MANAGE_LINE,
    MAP_LINE,
    MOVED_HEADLINE,
    SERVICE_LINE,
    WHEN_LINE,
)
from app.utilities.bookings.booking_manage_links import choose_maps_url
from app.utilities.channels.local_moments import format_local_moment

HEADLINES: dict[BookingConfirmationChange, LocalizedText] = {
    BookingConfirmationChange.BOOKED: CONFIRMED_HEADLINE,
    BookingConfirmationChange.MOVED: MOVED_HEADLINE,
}


@dataclass(frozen=True)
class ConfirmationFacts:
    """What one confirmation tells the guest."""

    business: BusinessDocument
    booking: BookingDocument
    booking_unit: BookingUnit
    service_title: KnowledgeTitle | None
    address: BusinessAddress | None
    manage_link: BookingManageLink | None
    change: BookingConfirmationChange
    language: LanguageTag


@dataclass(frozen=True)
class ConfirmationWriter:
    """Writes confirmations with the platform's localized lines."""

    text_resolver: LocalizedTextResolverContract

    def text(self, facts: ConfirmationFacts) -> MessageText:
        """One line per fact the booking has, the headline first."""

        lines: list[str] = [
            self._line(HEADLINES[facts.change], facts, business=facts.business.name)
        ]
        if facts.booking_unit is BookingUnit.NIGHT:
            lines.append(self._line(ARRIVAL_LINE, facts, when=self._start(facts)))
            lines.append(self._line(DEPARTURE_LINE, facts, when=self._end(facts)))
        else:
            lines.append(self._line(WHEN_LINE, facts, when=self._start(facts)))
        if facts.service_title is not None:
            lines.append(self._line(SERVICE_LINE, facts, service=facts.service_title))
        if int(facts.booking.party_size) > 1:
            lines.append(
                self._line(GUESTS_LINE, facts, party_size=int(facts.booking.party_size))
            )
        if facts.address is not None:
            lines.append(self._line(ADDRESS_LINE, facts, address=facts.address.text))
            maps_url = choose_maps_url(facts.address)
            if maps_url is not None:
                lines.append(self._line(MAP_LINE, facts, url=maps_url))
        if facts.manage_link is not None:
            lines.append(self._line(MANAGE_LINE, facts, url=facts.manage_link))
        return MessageText("\n".join(lines))

    def template_parameters(self, facts: ConfirmationFacts) -> list[MessageText] | None:
        """
        {{1}} business, {{2}} local date and time, {{3}} party size,
        {{4}} manage link; None without a link (the template needs it).
        """

        if facts.manage_link is None:
            return None

        return [
            MessageText(str(facts.business.name)),
            MessageText(self._start(facts)),
            MessageText(str(int(facts.booking.party_size))),
            MessageText(str(facts.manage_link)),
        ]

    def _line(
        self, text: LocalizedText, facts: ConfirmationFacts, **values: object
    ) -> str:
        return str(self.text_resolver.resolve(text, facts.language)).format(**values)

    def _start(self, facts: ConfirmationFacts) -> str:
        return format_local_moment(
            int(facts.booking.starts_at), facts.business.timezone, facts.language
        )

    def _end(self, facts: ConfirmationFacts) -> str:
        return format_local_moment(
            int(facts.booking.ends_at), facts.business.timezone, facts.language
        )
