"""The cabinet's booking list, booking views and the full-day availability grid."""

from datetime import datetime

import pytest

from app.schemas.constants.bookings import BookingOrder, BookingStatus, BookingUnit
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.bookings import AvailabilityQuery
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_integers import NightCount, PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate
from tests.operations.cabinet_bookings_helpers import Cabinet


def test_list_filters_by_local_dates_status_and_sandbox_and_is_audited() -> None:
    cabinet = Cabinet()
    # 01:00 local on Oct 6 is still Oct 5 in UTC.
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.table,
        cabinet.customer,
        "2026-10-06T01:00:00+04:00",
        "2026-10-06T02:00:00+04:00",
    )
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.table,
        cabinet.customer,
        "2026-10-07T19:00:00+04:00",
        "2026-10-07T21:00:00+04:00",
        status=BookingStatus.CANCELLED,
    )
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.hall,
        cabinet.customer,
        "2026-10-06T19:00:00+04:00",
        "2026-10-06T21:00:00+04:00",
        is_sandbox=True,
    )

    assert cabinet.list("2026-10-06", "2026-10-06") == ["2026-10-06 01:00 Giorgi"]
    assert cabinet.list(status=BookingStatus.CANCELLED) == ["2026-10-07 19:00 Giorgi"]
    assert len(cabinet.list(include_sandbox=True)) == 3
    entries = cabinet.world.audit_repo.list_by_business(cabinet.business.id)
    assert {(entry.action, entry.entity, entry.actor_id) for entry in entries} == {
        (AuditAction.VIEW, "booking", cabinet.staff_id)
    }
    with pytest.raises(ValidationFailedError):
        cabinet.list("2026-10-07", "2026-10-06")


def test_clock_is_the_injected_one() -> None:
    cabinet = Cabinet()
    cabinet.world.clock.move_to(datetime.fromisoformat("2026-10-06T15:30:00+00:00"))

    with pytest.raises(ValidationFailedError, match="too soon"):
        cabinet.world.create_manual_booking().run(cabinet.manual(time="19:00"))


def test_list_pages_by_start_time_and_filters_by_resource() -> None:
    cabinet = Cabinet()
    for day in ("2026-10-08", "2026-10-06", "2026-10-07"):
        cabinet.world.add_booking(
            cabinet.business,
            cabinet.table,
            cabinet.customer,
            f"{day}T19:00:00+04:00",
            f"{day}T21:00:00+04:00",
        )
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.hall,
        cabinet.customer,
        "2026-10-06T13:00:00+04:00",
        "2026-10-06T15:00:00+04:00",
    )

    first = cabinet.page(size=2)
    second = cabinet.page(size=2, cursor=first)
    latest = cabinet.page(order=BookingOrder.LATEST_FIRST, size=1)
    tables = cabinet.page(resource_id=cabinet.table.id)

    assert [(item.date, item.time) for item in first.items] == [
        ("2026-10-06", "13:00"),
        ("2026-10-06", "19:00"),
    ]
    assert first.next_cursor is not None
    assert [item.date for item in second.items] == ["2026-10-07", "2026-10-08"]
    assert second.next_cursor is None
    assert [item.date for item in latest.items] == ["2026-10-08"]
    assert {item.resource_name for item in tables.items} == {"Table 4"}
    assert len(tables.items) == 3


def test_booking_view_carries_creation_reminder_and_language() -> None:
    cabinet = Cabinet()
    conversation = cabinet.world.add_conversation(cabinet.business, cabinet.customer)

    result = cabinet.world.create_manual_booking().run(
        cabinet.manual(phone=None, language="ru", conversation_id=conversation.id)
    )
    listed = cabinet.page().items[0]

    assert listed.id == result.booking.id
    assert listed.language == "ru"
    assert listed.reminder_sent_at is None
    assert listed.created_at == cabinet.world.clock.now_microseconds()
    assert listed.conversation_id == conversation.id


class TestFullDayAvailability:
    def query(self, cabinet: Cabinet, party_size: int, full_day: bool) -> list[str]:
        result = cabinet.world.check_availability().run(
            AvailabilityQuery(
                business_id=cabinet.business.id,
                date=LocalDate("2026-10-05"),
                party_size=PartySize(party_size),
                full_day=full_day,
            )
        )
        return [f"{slot.time} {slot.resource_name}" for slot in result.slots]

    def test_lists_every_slot_of_every_resource_from_now(self) -> None:
        cabinet = Cabinet()
        # 12:00 local; the profile asks for 60 minutes of notice online.
        cabinet.world.clock.move_to(datetime.fromisoformat("2026-10-05T12:00:00+04:00"))

        slots = self.query(cabinet, 2, full_day=True)
        online = self.query(cabinet, 2, full_day=False)

        assert slots[:4] == [
            "12:00 Table 4",
            "12:00 Banquet hall",
            "12:30 Table 4",
            "12:30 Banquet hall",
        ]
        assert len(slots) > 10
        assert online[0] == "13:00 Table 4"
        assert len(online) == 10

    def test_ignores_the_online_party_limit(self) -> None:
        cabinet = Cabinet()

        assert self.query(cabinet, 30, full_day=True)[0].endswith("Banquet hall")
        with pytest.raises(ValidationFailedError):
            self.query(cabinet, 30, full_day=False)

    def test_lists_every_free_stay(self) -> None:
        cabinet = Cabinet()
        for number in range(1, 13):
            cabinet.world.add_resource(
                cabinet.business,
                f"Room {number:02d}",
                kind=cabinet.table.kind,
                booking_unit=BookingUnit.NIGHT,
            )

        result = cabinet.world.check_availability().run(
            AvailabilityQuery(
                business_id=cabinet.business.id,
                date=LocalDate("2026-10-06"),
                nights=NightCount(2),
                full_day=True,
            )
        )

        stays = [
            slot for slot in result.slots if slot.booking_unit is BookingUnit.NIGHT
        ]
        assert len(stays) == 12
