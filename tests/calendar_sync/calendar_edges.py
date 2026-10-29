"""The calendars outside the platform as the test's fakes, in a container."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, cast

from dependency_injector import providers

from app.containers.app import AppContainer
from app.facilitators.calendar_sync.ical_busy_reader import IcalBusyReader
from tests.calendar_sync.calendar_feed_server import CalendarFeedServer
from tests.calendar_sync.fake_cal_com import FakeCalCom


class _Overridable(Protocol):
    def override(self, provider: object) -> object: ...


def _replace(provider: object, value: object) -> None:
    cast(_Overridable, provider).override(providers.Object(value))


@dataclass
class CalendarEdges:
    """iCal feeds and Cal.com: nothing leaves the test."""

    feeds: CalendarFeedServer = field(default_factory=CalendarFeedServer)
    cal_com: FakeCalCom = field(default_factory=FakeCalCom)

    def install(self, container: AppContainer) -> None:
        calendars = container.facilitators.calendars
        _replace(
            calendars.ical_reader,
            IcalBusyReader(self.feeds, container.adapters.secret_cipher()),
        )
        _replace(calendars.cal_com_client, self.cal_com.client())

    def preparing(self) -> Callable[[AppContainer], None]:
        """For `start_workshop(prepare=...)`."""

        return self.install
