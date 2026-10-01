from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.repositories import RepositoriesContainer


class RegistriesContainer(containers.DeclarativeContainer):
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
