"""A platform brake a test sets by hand, for the work it holds back."""

from typed_time_provider import Microseconds

from app.contracts.platform_safety import PlatformBrakeRegistryContract
from app.schemas.constants.spend import PlatformBrake


class SetPlatformBrakes(PlatformBrakeRegistryContract):
    """No brake holds until a test sets `brake`; every reading is kept."""

    def __init__(self, brake: PlatformBrake | None = None) -> None:
        self.brake: PlatformBrake | None = brake
        self.readings: list[Microseconds] = []

    def current_brake(self, now: Microseconds) -> PlatformBrake | None:
        self.readings.append(now)
        return self.brake
