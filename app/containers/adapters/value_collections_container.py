from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.conversation_topics import ConversationTopicsDocument
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.domain.value_settings import (
    DigestPreferencesDocument,
    ValueSettingsDocument,
)


class ValueCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of what the assistant is worth (migration
    1061): each business's average check, each owner's digest choices and
    the stored digests and monthly reports; and what customers ask about
    (1100). A sibling of
    DocumentCollectionsContainer with the same storage factory (Postgres
    with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    value_settings_collection = document_collection(
        ValueSettingsDocument,
        "value_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
    digest_preferences_collection = document_collection(
        DigestPreferencesDocument,
        "digest_preferences",
        config,
        clients,
        utilities,
        time_provider,
    )
    value_report_collection = document_collection(
        ValueReportDocument,
        "value_reports",
        config,
        clients,
        utilities,
        time_provider,
    )
    conversation_topics_collection = document_collection(
        ConversationTopicsDocument,
        "conversation_topics",
        config,
        clients,
        utilities,
        time_provider,
    )
