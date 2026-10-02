from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.use_cases.assistant_use_cases import AssistantUseCasesContainer
from app.containers.use_cases.demo_use_cases import DemoUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.demo.seed_demo_data_orchestrator import (
    SeedDemoDataOrchestrator,
)
from app.schemas.dto.demo_data import DemoDataSeedReport, SeedDemoDataCommand


class DemoOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Development demo data (SEED_DEMO_DATA, API startup): the accounts, then
    per business its foundation, an assembled assistant version and its
    activity.
    """

    demo_use_cases: DemoUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    assistant_use_cases: AssistantUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    seed_demo_data_orchestrator: Factory[
        OrchestratorContract[SeedDemoDataCommand, DemoDataSeedReport]
    ] = Factory(
        SeedDemoDataOrchestrator,
        prepare_demo_accounts=demo_use_cases.prepare_demo_accounts_use_case,
        store_demo_foundation=demo_use_cases.store_demo_foundation_use_case,
        assemble_assistant_version=assistant_use_cases.assemble_assistant_version_use_case,
        store_demo_activity=demo_use_cases.store_demo_activity_use_case,
    )
