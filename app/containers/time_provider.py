from dependency_injector import containers
from dependency_injector.providers import Singleton
from typed_time_provider import MonotonicClock, Nanoseconds, WallClock


class TimeProviderContainer(containers.DeclarativeContainer):
    monotonic_clock: Singleton[MonotonicClock[Nanoseconds]] = Singleton(
        MonotonicClock,
        preferred_time_unit_type=Nanoseconds,
    )
    wall_clock: Singleton[WallClock[Nanoseconds]] = Singleton(
        WallClock,
        preferred_time_unit_type=Nanoseconds,
    )
