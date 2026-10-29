"""When a colleague can answer the customer after a handoff."""

from datetime import datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument, OpeningInterval
from app.schemas.dto.operations.message_texts import HandoffCustomerMessageInput
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.scheduling.opening_hours import (
    business_day_ranges,
    find_next_opening,
    is_open_at,
)
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    minute_of_day,
    to_local_date,
    to_time_of_day,
)


def build_customer_message_input(
    business: BusinessDocument,
    language: LanguageTag,
    now: Microseconds,
    profile: BusinessProfileDocument | None,
    schedule_exception_repo: ScheduleExceptionRepoContract,
) -> HandoffCustomerMessageInput:
    """
    "A colleague replies soon" while the business is open (or its hours
    are unknown); otherwise the local date and time it opens again.
    """

    hours: list[OpeningInterval] = [] if profile is None else list(profile.hours)
    if not hours:
        return HandoffCustomerMessageInput(language=language)

    zone: ZoneInfo = load_time_zone(business.timezone)
    ranges_starting_on = business_day_ranges(
        hours, schedule_exception_repo.list_by_business(business.id)
    )
    now_seconds: int = microseconds_to_seconds(int(now))
    if is_open_at(now_seconds, zone, ranges_starting_on):
        return HandoffCustomerMessageInput(language=language)

    reopening: datetime | None = find_next_opening(
        now_seconds, zone, ranges_starting_on
    )
    if reopening is None:
        return HandoffCustomerMessageInput(language=language)

    return HandoffCustomerMessageInput(
        language=language,
        reopens_on=to_local_date(reopening.date()),
        reopens_at=to_time_of_day(minute_of_day(reopening)),
    )
