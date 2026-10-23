"""
The seam between the provider graph and the typed provider resilience
(app/containers/adapters/provider_resilience.py, ADR 0010).
"""

from dependency_injector.providers import Singleton

from app.containers.adapters.provider_resilience import (
    ProviderResilience,
    build_provider_resilience,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer


def provider_resilience(
    *,
    clients: ClientsContainer,
    config: ConfigContainer,
    time_provider: TimeProviderContainer,
    utilities: UtilitiesContainer,
) -> Singleton[ProviderResilience]:
    """
    The process's one ProviderResilience, its parts taken from the graph:
    the single seam between the providers and the typed module
    (app/containers/adapters/provider_resilience.py).
    """

    return Singleton(
        build_provider_resilience,
        telegram_bot_client=clients.telegram_bot_client,
        smtp_email_client=clients.smtp_email_client,
        twilio_messaging_client=clients.twilio_messaging_client,
        flitt_client=clients.flitt_client,
        stripe_client=clients.stripe_client,
        settings=config.app_settings,
        monotonic_clock=time_provider.monotonic_clock,
        wall_clock=time_provider.microsecond_wall_clock,
        metrics=utilities.service_metrics,
    )
