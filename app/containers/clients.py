from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.config import ConfigContainer


class ClientsContainer(containers.DeclarativeContainer):
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
