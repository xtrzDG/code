from typed_time_provider import Microseconds

from app.contracts.platform_safety import (
    PlatformBrakeRegistryContract,
    PlatformPauseRepoContract,
    PlatformSpendGaugeContract,
)
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.spend import PlatformBrake
from app.utilities.spend.platform_brakes import read_platform_brake


class PlatformBrakeRegistry(PlatformBrakeRegistryContract):
    """
    The platform's brakes for work outside a customer's turn or call: the
    global pause (one keyed read) and the daily budget stop (the shared
    spend gauge, one sum a minute per process). The spend guard reads the
    same brakes before every model turn and call (`read_platform_brake`).
    """

    def __init__(
        self,
        platform_pause_repo: PlatformPauseRepoContract,
        platform_spend_gauge: PlatformSpendGaugeContract,
        settings: SpendGuardSettings,
    ) -> None:
        self._pause_repo: PlatformPauseRepoContract = platform_pause_repo
        self._spend_gauge: PlatformSpendGaugeContract = platform_spend_gauge
        self._settings: SpendGuardSettings = settings

    def current_brake(self, now: Microseconds) -> PlatformBrake | None:
        return read_platform_brake(
            self._pause_repo, self._spend_gauge, self._settings, now
        ).brake
