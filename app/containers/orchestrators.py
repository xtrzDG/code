from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.use_cases import UseCasesContainer


class OrchestratorsContainer(containers.DeclarativeContainer):
    use_cases: UseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
