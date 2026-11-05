from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.public_demo_use_cases import (
    PublicDemoUseCasesContainer,
)
from app.containers.utilities import UtilitiesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.demo.list_public_demos_orchestrator import (
    ListPublicDemosOrchestrator,
)
from app.schemas.dto.public_demo import PublicDemoList, PublicDemoListQuery


class PublicDemoOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the landing page's sandbox demos: the list (each demo
    described in its own business's storage scope), a visitor's message
    admitted, and the turn told back.
    """

    public_demo_use_cases: PublicDemoUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    list_public_demos_orchestrator: Factory[
        OrchestratorContract[PublicDemoListQuery, PublicDemoList]
    ] = Factory(
        ListPublicDemosOrchestrator,
        list_demo_businesses=public_demo_use_cases.list_public_demo_businesses_use_case,
        describe_public_demo=public_demo_use_cases.describe_public_demo_use_case,
        storage_scope=utilities.storage_scope,
    )
    admit_public_demo_message_orchestrator = use_case_orchestrator(
        public_demo_use_cases.admit_public_demo_message_use_case
    )
    summarize_public_demo_reply_orchestrator = use_case_orchestrator(
        public_demo_use_cases.summarize_public_demo_reply_use_case
    )
