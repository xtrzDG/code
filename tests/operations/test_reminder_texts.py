"""The reminder text: the customer's language, the business time zone and stays."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, BookingUnit, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.typings.bookings.constrained_integers import (
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.profiles.strings import CancellationPolicyText
from app.transformers.notifications.booking_reminder_transformer import (
    BookingReminderTransformer,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.operations.reminder_scene import ReminderScene


@pytest.mark.parametrize(
    ("language", "expected_start"),
    [
        ("en", "Reminder: your booking at Salobie Bia"),
        ("ru", "Напоминание: ваша бронь в «Salobie Bia»"),
        ("ru-RU", "Напоминание: ваша бронь"),
        ("tr", "Reminder: your booking"),  # no Turkish text: English
        (None, "შეხსენება"),  # unknown language: the business default (ka)
    ],
)
def test_reminder_language_follows_the_customer(
    language: str | None,
    expected_start: str,
) -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"}, language=language)
    scene.add_booking(contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM)

    scene.run()

    [(_, _, _, text)] = scene.sender.sent
    assert str(text).startswith(expected_start)


def test_business_time_zone_of_another_country_is_used() -> None:
    scene = ReminderScene()
    rome = scene.world.add_business(
        name="Trattoria Roma",
        country_code="IT",
        timezone="Europe/Rome",
        currency_code="EUR",
        languages=("it", "en"),
        owner_language="it",
    )
    scene.world.add_profile(rome, cancellation_policy=None)
    table = scene.world.add_resource(rome, "Tavolo 1")
    contact = scene.add_customer(
        {ChannelKind.MESSENGER: "psid-1"}, language="en", business=rome
    )
    scene.customer_wrote(contact, ChannelKind.MESSENGER, hours_ago=5, business=rome)
    scene.add_booking(
        contact,
        "2026-10-05T18:00:00+00:00",
        ChannelKind.MESSENGER,
        business=rome,
        resource=table,
    )

    scene.run()

    [(business_id, channel, _, text)] = scene.sender.sent
    assert business_id == rome.id
    assert channel is ChannelKind.MESSENGER
    assert "Trattoria Roma" in str(text)
    assert "20:00" in str(text)  # 18:00 UTC is 20:00 in Rome (CEST)
    assert "Cancellation policy" not in str(text)


def test_hotel_stay_reminder_names_the_check_in() -> None:
    scene = ReminderScene()
    hotel = scene.world.add_business(name="Old Tbilisi Hotel", niche_key=NicheKey.HOTEL)
    scene.world.add_profile(hotel, resource_kind=ResourceKind.ROOM, slot_minutes=1440)
    room = scene.world.add_resource(
        hotel,
        "Double room",
        kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.NIGHT,
    )
    contact = scene.add_customer(
        {ChannelKind.TELEGRAM: "7001"}, language="en", business=hotel
    )
    scene.add_booking(
        contact,
        "2026-10-05T10:00:00+00:00",
        ChannelKind.TELEGRAM,
        business=hotel,
        resource=room,
    )

    scene.run()

    [(_, _, _, text)] = scene.sender.sent
    assert str(text).startswith("Reminder: your stay at Old Tbilisi Hotel")
    assert "check-in from 14:00" in str(text)


def build_message_input(
    language: str,
    unit: BookingUnit = BookingUnit.TIME_SLOT,
    policy: str | None = None,
) -> BookingMessageInput:
    return BookingMessageInput(
        business_name=BusinessName("Salobie Bia"),
        booking=BookingView(
            id=BookingId(),
            business_id=BusinessId(),
            resource_id=ResourceId(),
            resource_name=ResourceName("Table 1"),
            contact_id=ContactId(),
            contact_name=ContactName("Giorgi"),
            date=LocalDate("2026-10-06"),
            time=LocalTimeOfDay("19:30"),
            end_date=LocalDate("2026-10-06"),
            end_time=LocalTimeOfDay("21:30"),
            timezone=TimezoneName("Asia/Tbilisi"),
            party_size=PartySize(4),
            status=BookingStatus.CONFIRMED,
            source_channel=ChannelKind.WHATSAPP,
            created_at=Microseconds(1_790_000_000_000_000),
        ),
        booking_unit=unit,
        language=LanguageTag(language),
        cancellation_policy=None if policy is None else CancellationPolicyText(policy),
    )


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (
            "en",
            "Reminder: your booking at Salobie Bia is on Tuesday, October 6, 2026 "
            "at 19:30. Name: Giorgi. Guests: 4. To cancel or change it, just reply "
            "to this message.",
        ),
        (
            "ru",
            "Напоминание: ваша бронь в «Salobie Bia» — вторник, 6 октября "
            "2026\u202fг., 19:30. Имя: Giorgi. Гостей: 4. Чтобы отменить или "
            "перенести бронь, просто ответьте на это сообщение.",
        ),
    ],
)
def test_reminder_text(language: str, expected: str) -> None:
    transformer = BookingReminderTransformer(LocalizedTextResolver())

    text = transformer.transform(build_message_input(language))

    assert str(text) == expected


def test_reminder_text_in_georgian_with_the_cancellation_policy() -> None:
    transformer = BookingReminderTransformer(LocalizedTextResolver())

    text = str(
        transformer.transform(
            build_message_input("ka", policy="უფასო გაუქმება 2 საათით ადრე.")
        )
    )

    first_line, policy_line = text.split("\n")
    assert first_line.startswith("შეხსენება: თქვენი ჯავშანი Salobie Bia-ში")
    assert "19:30" in first_line
    assert policy_line == "გაუქმების წესები: უფასო გაუქმება 2 საათით ადრე."


def test_stay_reminder_text() -> None:
    transformer = BookingReminderTransformer(LocalizedTextResolver())

    text = str(transformer.transform(build_message_input("ru", BookingUnit.NIGHT)))

    assert text.startswith("Напоминание: ваше проживание в «Salobie Bia»")
    assert "заезд с 19:30" in text
