# Typed surface of recurring-ical-events (it ships no py.typed): the one
# query the iCal import uses, every occurrence of a calendar's events
# between two moments.

import datetime

from icalendar import Component

class CalendarQuery:
    def between(
        self,
        start: datetime.date | datetime.datetime,
        stop: datetime.date | datetime.datetime,
    ) -> list[Component]: ...

def of(
    a_calendar: Component,
    keep_recurrence_attributes: bool = False,
    components: tuple[str, ...] = ("VEVENT",),
    skip_bad_series: bool = False,
) -> CalendarQuery: ...
