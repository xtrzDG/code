from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.campaigns import (
    CampaignMessageDocument,
    CampaignSettingsDocument,
)
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistSettingsDocument


class GrowthCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the revenue features (migration 1151): the
    waitlist's settings and entries, the campaigns' settings and messages.
    A sibling of DocumentCollectionsContainer with the same storage factory
    (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    waitlist_entry_collection = document_collection(
        WaitlistEntryDocument,
        "waitlist_entries",
        config,
        clients,
        utilities,
        time_provider,
    )
    waitlist_settings_collection = document_collection(
        WaitlistSettingsDocument,
        "waitlist_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
    campaign_settings_collection = document_collection(
        CampaignSettingsDocument,
        "campaign_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
    campaign_message_collection = document_collection(
        CampaignMessageDocument,
        "campaign_messages",
        config,
        clients,
        utilities,
        time_provider,
    )
