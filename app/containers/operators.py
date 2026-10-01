from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines import PipelinesContainer


class OperatorsContainer(containers.DeclarativeContainer):
    pipelines: PipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
