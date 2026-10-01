from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters import AdaptersContainer
from app.containers.config import ConfigContainer


class FacilitatorsContainer(containers.DeclarativeContainer):
    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
