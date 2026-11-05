"""The checks of a text-back, built from the call use cases' container edges."""

from dependency_injector.providers import Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.utilities import UtilitiesContainer
from app.use_cases.voice.call_settings.text_back_template_check import (
    TextBackTemplateCheck,
)
from app.use_cases.voice.missed_calls.text_back_destinations import (
    TextBackSmsDestinations,
)


def text_back_sms_destinations_factory(
    registries: RegistriesContainer, utilities: UtilitiesContainer
) -> Factory[TextBackSmsDestinations]:
    """Where a text-back SMS may go (the login codes' destination rules)."""

    return Factory(
        TextBackSmsDestinations,
        high_cost_registry=registries.high_cost_phone_number_registry,
        country_registry=registries.country_registry,
        phone_number_parser=utilities.phone_number_parser,
    )


def text_back_template_check_factory(
    clients: ClientsContainer,
    repositories: RepositoriesContainer,
    adapters: AdaptersContainer,
    config: ConfigContainer,
) -> Factory[TextBackTemplateCheck]:
    """A text-back's WhatsApp template must not be a MARKETING one (VOICE-09)."""

    return Factory(
        TextBackTemplateCheck,
        catalog=clients.meta_template_catalog_client,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        app_settings=config.app_settings,
    )
