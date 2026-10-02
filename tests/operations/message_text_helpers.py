"""Booking views and message inputs for the customer and staff text tests."""

from datetime import date

from babel.dates import format_date
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import (
    BookingStatus,
    BookingUnit,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations.message_texts import (
    BookingMessageInput,
    BookingStaffNotificationInput,
)
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import BookingNote, ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.schemas.typings.profiles.strings import CancellationPolicyText
from app.utilities.scheduling.localized_formatting import (
    find_locale,
)
from tests.operations.fakes import FakeLocalizedTextResolver

CUSTOMER_LANGUAGES: tuple[str, ...] = (
    "en",
    "ru",
    "ka",
    "tr",
    "he",
    "ar",
    "hy",
    "uk",
    "de",
    "fr",
    "es",
    "it",
)


RESOLVER = FakeLocalizedTextResolver()


def booking_view(
    day: str = "2026-10-06",
    time: str = "19:30",
    end_day: str | None = None,
    end_time: str = "21:30",
    notes: str | None = None,
) -> BookingView:
    return BookingView(
        id=BookingId(),
        business_id=BusinessId(),
        resource_id=ResourceId(),
        resource_name=ResourceName("Table 4"),
        contact_id=ContactId(),
        contact_name=ContactName("Nino Kapanadze"),
        contact_phone_number=E164PhoneNumber("+995555123456"),
        date=LocalDate(day),
        time=LocalTimeOfDay(time),
        end_date=LocalDate(end_day or day),
        end_time=LocalTimeOfDay(end_time),
        timezone=TimezoneName("Asia/Tbilisi"),
        party_size=PartySize(5),
        status=BookingStatus.CONFIRMED,
        source_channel=ChannelKind.INSTAGRAM,
        notes=None if notes is None else BookingNote(notes),
        created_at=Microseconds(1_790_000_000_000_000),
    )


def full_date(day: date, language: str) -> str:
    return format_date(day, "full", locale=find_locale(LanguageTag(language)))


def message_input(
    language: str,
    booking: BookingView | None = None,
    booking_unit: BookingUnit = BookingUnit.TIME_SLOT,
    policy: str | None = None,
) -> BookingMessageInput:
    return BookingMessageInput(
        business_name=BusinessName("Salobie Bia"),
        booking=booking or booking_view(),
        booking_unit=booking_unit,
        language=LanguageTag(language),
        cancellation_policy=None if policy is None else CancellationPolicyText(policy),
    )


def staff_input(
    language: str, notes: str | None = None
) -> BookingStaffNotificationInput:
    return BookingStaffNotificationInput(
        business_name=BusinessName("Salobie Bia"),
        booking=booking_view(notes=notes),
        contact_phone_display=FormattedPhoneNumber("+995 555 12 34 56"),
        language=LanguageTag(language),
    )
