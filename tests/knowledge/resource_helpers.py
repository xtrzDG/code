"""Adding resources and schedule exceptions through the knowledge harness."""

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.resources import (
    CreateResourceCommand,
    CreateScheduleExceptionCommand,
    ResourceInput,
    ResourceView,
    ScheduleExceptionInput,
    ScheduleExceptionView,
)
from app.schemas.typings.bookings.constrained_integers import ResourceCapacity
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import ResourceName, ScheduleExceptionNote
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from tests.knowledge.harness import KnowledgeHarness


def hours(weekday: Weekday, opens: int, closes: int) -> OpeningInterval:
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(opens),
        closes_at=ClosingMinuteOfDay(closes),
    )


def add_resource(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    name: str,
    **fields: object,
) -> ResourceView:
    resource_input = ResourceInput.model_validate(
        {"name": ResourceName(name), "capacity": ResourceCapacity(4), **fields}
    )
    return harness.create_resource.run(
        CreateResourceCommand(business_id=business.id, resource=resource_input)
    )


def add_exception(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    date: str,
    resource_id: ResourceId | None = None,
    special_hours: list[OpeningInterval] | None = None,
    note: str | None = None,
) -> ScheduleExceptionView:
    return harness.create_schedule_exception.run(
        CreateScheduleExceptionCommand(
            business_id=business.id,
            exception=ScheduleExceptionInput(
                resource_id=resource_id,
                date=LocalDate(date),
                is_closed_all_day=special_hours is None,
                special_hours=special_hours or [],
                note=None if note is None else ScheduleExceptionNote(note),
            ),
        )
    )
