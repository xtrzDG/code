"""
The platform's brakes (1230), one per process for every context through
the facilitators' container: the daily budget stop's spend gauge (one sum
of the day's usage a minute) and the brake it makes with the global
pause, which background model work and the owners' costly actions read.
The spend guard reads the same gauge before every model turn and call.
"""

from dependency_injector.providers import Singleton

from app.containers.config import ConfigContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.utilities import UtilitiesContainer
from app.registries.limits.platform_brake_registry import PlatformBrakeRegistry
from app.registries.limits.platform_spend_gauge_registry import (
    PlatformSpendGaugeRegistry,
)


def platform_brake_providers(
    config: ConfigContainer,
    repositories: RepositoriesContainer,
    utilities: UtilitiesContainer,
) -> tuple[Singleton[PlatformSpendGaugeRegistry], Singleton[PlatformBrakeRegistry]]:
    gauge: Singleton[PlatformSpendGaugeRegistry] = Singleton(
        PlatformSpendGaugeRegistry,
        usage_spend_repo=repositories.usage_spend_repo,
        storage_scope=utilities.storage_scope,
    )
    return gauge, Singleton(
        PlatformBrakeRegistry,
        platform_pause_repo=repositories.platform_pause_repo,
        platform_spend_gauge=gauge,
        settings=config.app_settings.provided.spend_guard,
    )
