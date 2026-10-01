from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer


class AdaptersContainer(containers.DeclarativeContainer):
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
