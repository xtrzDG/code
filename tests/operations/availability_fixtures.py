"""A Tbilisi restaurant for availability tests and a reader of offered times."""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import AvailabilityQuery, AvailabilityResult
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from tests.operations.operations_world import OperationsWorld


class RestaurantFixture:
    """Tbilisi restaurant open 12:00-23:00, 2 h slots, 60 min notice."""

    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.business: BusinessDocument = self.world.add_business()
        self.world.add_profile(self.business)
        self.table_for_two: ResourceDocument = self.world.add_resource(
            self.business, "Table 2", capacity=2
        )
        self.table_for_four: ResourceDocument = self.world.add_resource(
            self.business, "Table 4", capacity=4
        )
        self.table_for_eight: ResourceDocument = self.world.add_resource(
            self.business, "Table 8", capacity=8
        )
        self.contact: ContactDocument = self.world.add_contact(self.business, "Giorgi")

    def query(
        self,
        day: str = "2026-10-05",
        time: str | None = None,
        party_size: int | None = None,
        is_sandbox: bool = False,
        resource_id: ResourceId | None = None,
        duration_minutes: int | None = None,
    ) -> AvailabilityResult:
        return self.world.check_availability().run(
            AvailabilityQuery(
                business_id=self.business.id,
                date=LocalDate(day),
                time=None if time is None else LocalTimeOfDay(time),
                party_size=None if party_size is None else PartySize(party_size),
                is_sandbox=is_sandbox,
                resource_id=resource_id,
                duration_minutes=(
                    None
                    if duration_minutes is None
                    else BookingDurationMinutes(duration_minutes)
                ),
            )
        )


def times(result: AvailabilityResult) -> list[str]:
    return [str(slot.time) for slot in result.slots]
