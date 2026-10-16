from dependency_injector import containers
from dependency_injector.providers import Singleton
from typed_time_provider import Microseconds, MonotonicClock, Nanoseconds, WallClock


class TimeProviderContainer(containers.DeclarativeContainer):
    monotonic_clock: Singleton[MonotonicClock[Nanoseconds]] = Singleton(
        MonotonicClock,
        preferred_time_unit_type=Nanoseconds,
    )
    wall_clock: Singleton[WallClock[Nanoseconds]] = Singleton(
        WallClock,
        preferred_time_unit_type=Nanoseconds,
    )
    # "Now" of every business module (conventions: WallClock[Microseconds]).
    microsecond_wall_clock: Singleton[WallClock[Microseconds]] = Singleton(
        WallClock,
        preferred_time_unit_type=Microseconds,
    )
