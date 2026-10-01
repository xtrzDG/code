from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters import AdaptersContainer


class RepositoriesContainer(containers.DeclarativeContainer):
    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
