"""A service's buffer keeps its master busy after the visit, both ways."""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes
from app.utilities.scheduling.availability import blocked_until
from tests.bookings.salon_fixture import TOMORROW, Salon
from tests.operations.builders import seconds


def visit(
    salon: Salon,
    master: ResourceDocument,
    starts: str,
    ends: str,
    buffer: int | None = None,
    status: BookingStatus = BookingStatus.CONFIRMED,
) -> BookingDocument:
    """A stored visit of `master` tomorrow, local times, with its buffer."""

    booking = salon.world.add_booking(
        salon.business,
        master,
        salon.contact,
        f"{TOMORROW}T{starts}:00+04:00",
        f"{TOMORROW}T{ends}:00+04:00",
        status=status,
        party_size=1,
    ).model_copy(
        update={"buffer_minutes": None if buffer is None else BufferMinutes(buffer)}
    )
    salon.world.booking_repo.save(booking)
    return booking


def nino_times(salon: Salon) -> list[str]:
    result = salon.query(service="Haircut", resource="Nino", time="12:00")
    return [str(slot.time) for slot in result.slots]


def test_a_visit_ends_its_buffer_later_for_the_next_one() -> None:
    salon = Salon()
    visit(salon, salon.nino, "11:00", "11:30", buffer=15)

    # 11:30 would fit right after the visit, but Nino rests until 11:45.
    assert "11:30" not in nino_times(salon)
    assert "12:00" in nino_times(salon)


def test_without_a_buffer_the_next_visit_starts_at_the_end() -> None:
    salon = Salon()
    visit(salon, salon.nino, "11:00", "11:30")

    assert "11:30" in nino_times(salon)


def test_the_new_visit_needs_room_for_its_own_buffer() -> None:
    salon = Salon()
    # Nino's next visit starts at 11:50: a haircut at 11:00 ends at 11:45,
    # and its 15-minute buffer would run into it.
    visit(salon, salon.nino, "11:50", "12:20")

    assert "11:00" not in nino_times(salon)
    with pytest.raises(ConflictError):
        salon.book(service="Haircut", resource="Nino", time="11:00")

    # Without the buffer a 45-minute visit at 11:00 would have fitted.
    salon.world.knowledge_repo.save(
        salon.haircut.model_copy(update={"buffer_minutes": None})
    )
    assert "11:00" in nino_times(salon)


def test_booking_into_a_buffer_is_refused_and_after_it_succeeds() -> None:
    salon = Salon()
    salon.book(service="Haircut", resource="Nino", time="12:00")

    with pytest.raises(ConflictError):
        salon.book(service="Haircut", resource="Nino", time="12:45")

    result = salon.book(service="Haircut", resource="Nino", time="13:00")
    assert result.booking.time == "13:00"


def test_cancelled_visits_keep_no_buffer() -> None:
    salon = Salon()
    visit(salon, salon.nino, "11:00", "11:30", 15, BookingStatus.CANCELLED)

    assert "11:30" in nino_times(salon)


def test_the_unit_is_free_again_after_the_end_and_the_buffer() -> None:
    salon = Salon()
    buffered = visit(salon, salon.nino, "11:00", "11:30", buffer=15)
    plain = visit(salon, salon.levan, "11:00", "11:30")

    assert blocked_until(buffered) == seconds(f"{TOMORROW}T11:45:00+04:00")
    assert blocked_until(plain) == seconds(f"{TOMORROW}T11:30:00+04:00")


def test_rescheduling_keeps_the_buffer_and_the_performers_of_the_service() -> None:
    salon = Salon()
    first = salon.book(service="Haircut", resource="Nino", time="12:00")
    salon.book(service="Haircut", resource="Nino", time="14:00")

    # 13:00 to 13:45 plus 15 minutes ends right when the 14:00 visit starts.
    moved = salon.reschedule(first.booking.id, "13:00")
    assert (moved.booking.resource_name, moved.booking.end_time) == ("Nino", "13:45")

    # At 13:15 the buffer runs into Nino's 14:00 visit: Levan, who also
    # cuts hair, takes it; Mariam, free as well, does not.
    moved = salon.reschedule(first.booking.id, "13:15")
    assert moved.booking.resource_name == "Levan"
    assert moved.booking.service_item_id == salon.haircut.id

    # The moved visit keeps its buffer: Levan rests until 14:15.
    with pytest.raises(ConflictError):
        salon.book(service="Haircut", resource="Levan", time="14:00")
