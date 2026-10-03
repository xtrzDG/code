from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.call_collections_container import CallCollectionsContainer
from app.repositories.call_follow_up_repositories import (
    CallSettingsRepository,
    MissedCallRepository,
)


class CallRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of what follows a phone call (migration 1051): callers
    who did not get through with their text-backs, and each business's
    call settings. `RepositoriesContainer` extends it, so they are read as
    `repositories.missed_call_repo` like every other repository.
    """

    call_collections: CallCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    missed_call_repo: Singleton[MissedCallRepository] = Singleton(
        MissedCallRepository, collection=call_collections.missed_call_collection
    )
    call_settings_repo: Singleton[CallSettingsRepository] = Singleton(
        CallSettingsRepository, collection=call_collections.call_settings_collection
    )
