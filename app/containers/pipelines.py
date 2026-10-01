from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators import OrchestratorsContainer


class PipelinesContainer(containers.DeclarativeContainer):
    orchestrators: OrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]
