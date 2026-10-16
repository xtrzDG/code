"""Staff book services from the cabinet and see them in the bookings list."""

import pytest

from app.schemas.constants.bookings import BookingRefusalCode
from app.schemas.dto.bookings import AvailabilityQuery
from app.schemas.dto.operations.bookings import ListBookingsQuery, ManualBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.booleans import IsFullDayAvailability
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from tests.bookings.salon_fixture import TOMORROW, Salon, reason_code


def manual(
    salon: Salon,
    service_item_id: KnowledgeItemId | None,
    time: str = "12:00",
    resource_id: ResourceId | None = None,
    duration: int | None = None,
) -> ManualBookingCommand:
    return ManualBookingCommand(
        business_id=salon.business.id,
        actor_id=salon.staff_id,
        contact_name=ContactName("Tamar"),
        contact_phone_number=RawPhoneNumberInput("555 12 34 56"),
        resource_id=resource_id,
        service_item_id=service_item_id,
        date=LocalDate(TOMORROW),
        time=LocalTimeOfDay(time),
        duration_minutes=None if duration is None else BookingDurationMinutes(duration),
        party_size=PartySize(1),
    )


def test_staff_book_a_service_with_its_length_buffer_and_value() -> None:
    salon = Salon()

    result = salon.world.create_manual_booking().run(manual(salon, salon.manicure.id))

    view = result.booking
    assert (view.resource_name, view.time, view.end_time) == (
        "Mariam",
        "12:00",
        "13:00",
    )
    assert (view.service_title, view.value_minor, view.currency_code) == (
        "Manicure",
        3000,
        "GEL",
    )


def test_staff_may_book_a_service_longer_than_usual() -> None:
    salon = Salon()

    result = salon.world.create_manual_booking().run(
        manual(salon, salon.haircut.id, resource_id=salon.levan.id, duration=90)
    )

    assert (result.booking.resource_name, result.booking.end_time) == (
        "Levan",
        "13:30",
    )
    # The buffer still follows the longer visit.
    with pytest.raises(ConflictError):
        salon.book(service="Haircut", resource="Levan", time="13:30")


def test_staff_cannot_give_a_service_to_someone_who_does_not_do_it() -> None:
    salon = Salon()

    with pytest.raises(ValidationFailedError) as error:
        salon.world.create_manual_booking().run(
            manual(salon, salon.haircut.id, resource_id=salon.mariam.id)
        )

    assert reason_code(error.value) == BookingRefusalCode.NOT_PERFORMED


def test_an_unknown_service_id_is_not_found() -> None:
    salon = Salon()

    with pytest.raises(NotFoundError):
        salon.world.create_manual_booking().run(manual(salon, KnowledgeItemId()))


def test_the_full_day_view_of_a_service_lists_every_performer() -> None:
    salon = Salon()

    result = salon.world.check_availability().run(
        AvailabilityQuery(
            business_id=salon.business.id,
            date=LocalDate(TOMORROW),
            service_item_id=salon.haircut.id,
            full_day=IsFullDayAvailability(True),
        )
    )

    at_noon = [slot for slot in result.slots if slot.time == "12:00"]
    assert {slot.resource_name for slot in at_noon} == {"Nino", "Levan"}


def test_the_bookings_list_names_each_service_and_value() -> None:
    salon = Salon()
    salon.book(service="Haircut", resource="Nino", time="12:00")
    salon.book(service=None, time="15:00")

    page = salon.world.list_bookings().run(
        ListBookingsQuery(business_id=salon.business.id, actor_id=salon.staff_id)
    )

    rows = [
        (str(view.time), view.service_title, view.value_minor) for view in page.items
    ]
    assert rows == [("12:00", "Haircut", 4500), ("15:00", None, None)]
