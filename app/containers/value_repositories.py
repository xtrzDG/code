from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.value_collections_container import (
    ValueCollectionsContainer,
)
from app.repositories.value_repositories import (
    DigestPreferencesRepository,
    ValueReportRepository,
    ValueSettingsRepository,
)


class ValueRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of what the assistant is worth (migration 1061): the
    average check, each owner's digest choices and the stored reports.
    `RepositoriesContainer` extends it, so they are read as
    `repositories.value_report_repo` like every other repository; the
    counts the value model adds to the dashboard's are `value_count_repo`.
    """

    value_collections: ValueCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    value_settings_repo: Singleton[ValueSettingsRepository] = Singleton(
        ValueSettingsRepository,
        collection=value_collections.value_settings_collection,
    )
    digest_preferences_repo: Singleton[DigestPreferencesRepository] = Singleton(
        DigestPreferencesRepository,
        collection=value_collections.digest_preferences_collection,
    )
    value_report_repo: Singleton[ValueReportRepository] = Singleton(
        ValueReportRepository,
        collection=value_collections.value_report_collection,
    )
