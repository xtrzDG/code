"""Booking a service with a specific master: performers, lengths and values."""

import pytest

from app.schemas.constants.bookings import BookingRefusalCode
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from tests.bookings.salon_fixture import Salon, reason_code
from tests.operations.builders import seconds


def test_a_45_minute_haircut_with_nino_books_nino_and_carries_its_value() -> None:
    salon = Salon()

    result = salon.book(service="Haircut", resource="Nino", time="12:00")

    view = result.booking
    assert view.resource_name == "Nino"
    assert (view.date, view.time, view.end_time) == ("2026-10-06", "12:00", "12:45")
    assert (view.service_item_id, view.service_title) == (salon.haircut.id, "Haircut")
    assert (view.value_minor, view.currency_code) == (4500, "GEL")
    stored = salon.world.bookings_of(salon.business.id)
    assert len(stored) == 1
    assert stored[0].resource_id == salon.nino.id
    assert int(stored[0].ends_at) == seconds("2026-10-06T12:45:00+04:00")
    assert stored[0].service_item_id == salon.haircut.id
    assert stored[0].buffer_minutes == 15
    assert (stored[0].value_minor, stored[0].currency_code) == (4500, "GEL")


def test_without_a_named_master_the_service_goes_to_a_free_performer_only() -> None:
    salon = Salon()
    salon.book(service="Haircut", resource="Nino", time="12:00")

    second = salon.book(service="Haircut", time="12:00")

    assert second.booking.resource_name == "Levan"
    # Mariam is free at 12:00 but does not cut hair.
    with pytest.raises(ConflictError):
        salon.book(service="Haircut", time="12:00")


def test_availability_of_a_service_offers_only_its_performers() -> None:
    salon = Salon()
    salon.book(service="Haircut", resource="Nino", time="12:00")
    salon.book(service="Haircut", resource="Levan", time="12:00")

    result = salon.query(service="haircut", time="12:00")

    # Mariam is free at 12:00 but does not cut hair; Nino and Levan are
    # busy until 13:00 (45 minutes and the 15-minute buffer).
    assert [str(slot.time) for slot in result.slots] == [
        "10:00",
        "10:30",
        "11:00",
        "13:00",
        "13:30",
    ]
    assert {slot.resource_name for slot in result.slots} <= {"Nino", "Levan"}
    assert {slot.duration_minutes for slot in result.slots} == {45}
    assert result.service is not None
    assert (result.service.id, result.service.title) == (salon.haircut.id, "Haircut")
    assert result.service.buffer_minutes == 15
    assert {performer.resource_name for performer in result.service.performers} == {
        "Nino",
        "Levan",
    }
    assert result.services == []


def test_availability_with_a_named_master_offers_only_that_master() -> None:
    salon = Salon()

    result = salon.query(service="Manicure", resource="Mariam", time="12:00")

    assert {slot.resource_name for slot in result.slots} == {"Mariam"}
    assert {slot.duration_minutes for slot in result.slots} == {60}


def test_without_a_service_availability_lists_the_bookable_services() -> None:
    salon = Salon()

    result = salon.query(time="12:00")

    assert result.service is None
    assert [(offer.title, offer.id) for offer in result.services] == [
        ("Haircut", salon.haircut.id),
        ("Manicure", salon.manicure.id),
    ]
    manicure = result.services[1]
    assert [performer.resource_name for performer in manicure.performers] == ["Mariam"]
    assert (manicure.duration_minutes, manicure.price_minor) == (60, 3000)


def test_a_master_who_does_not_do_the_service_is_refused_with_who_does() -> None:
    salon = Salon()

    with pytest.raises(ValidationFailedError, match="Nino does not do this") as error:
        salon.book(service="Manicure", resource="Nino")

    assert reason_code(error.value) == BookingRefusalCode.NOT_PERFORMED
    assert "Mariam" in str(error.value)
    assert salon.world.bookings_of(salon.business.id) == []


def test_a_service_nobody_performs_asks_for_a_manager() -> None:
    salon = Salon()
    inactive = salon.mariam.model_copy(update={"is_active": False})
    salon.world.resource_repo.save(inactive)

    with pytest.raises(ValidationFailedError, match="pass the request") as error:
        salon.query(service="Manicure")

    assert reason_code(error.value) == BookingRefusalCode.NOT_PERFORMED


def test_a_service_is_found_by_its_id() -> None:
    salon = Salon()

    result = salon.book(service=str(salon.manicure.id), time="15:00")

    assert result.booking.resource_name == "Mariam"
    assert result.booking.end_time == "16:00"
    assert result.booking.value_minor == 3000


def test_an_unknown_service_lists_the_bookable_ones_with_their_ids() -> None:
    salon = Salon()

    with pytest.raises(ValidationFailedError, match="Pedicure") as error:
        salon.book(service="Pedicure")

    assert reason_code(error.value) == BookingRefusalCode.UNKNOWN_SERVICE
    assert f"Haircut (id {salon.haircut.id})" in str(error.value)
    assert f"Manicure (id {salon.manicure.id})" in str(error.value)


def test_two_services_matching_as_well_are_ambiguous() -> None:
    salon = Salon()
    salon.offer("Hair colouring", 90, 9000, performers=[salon.nino])
    salon.offer("Hair styling", 30, 3000, performers=[salon.nino])

    with pytest.raises(ValidationFailedError, match="several services") as error:
        salon.book(service="hair", resource="Nino")

    assert reason_code(error.value) == BookingRefusalCode.AMBIGUOUS_SERVICE
    assert "Hair colouring" in str(error.value)
    assert "Hair styling" in str(error.value)


def test_a_service_id_from_the_cabinet_must_be_an_active_offer() -> None:
    salon = Salon()
    retired = salon.haircut.model_copy(update={"is_active": False})
    salon.world.knowledge_repo.save(retired)

    assert salon.query(service_item_id=salon.manicure.id).service is not None
    for item_id in (KnowledgeItemId(), retired.id):
        with pytest.raises(NotFoundError, match="was not found"):
            salon.query(service_item_id=item_id)


def test_a_service_nobody_is_linked_to_falls_to_every_master() -> None:
    salon = Salon()
    salon.offer("Consultation", 30, 0)
    salon.book(service="Haircut", resource="Nino", time="12:00")
    salon.book(service="Haircut", resource="Levan", time="12:00")

    result = salon.book(service="Consultation", time="12:00")

    # Every master is linked to another service, so none is a generalist:
    # an offer nobody is linked to may go to any of them.
    assert result.booking.resource_name == "Mariam"
    assert result.booking.value_minor == 0
