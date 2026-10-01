from dependency_injector import containers
from dependency_injector.providers import Container

from app.containers.adapters import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.gateways import GatewaysContainer
from app.containers.operators import OperatorsContainer
from app.containers.orchestrators import OrchestratorsContainer
from app.containers.pipelines import PipelinesContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases import UseCasesContainer
from app.containers.utilities import UtilitiesContainer


class AppContainer(containers.DeclarativeContainer):
    config: ConfigContainer = Container(ConfigContainer)  # type: ignore[assignment]
    clients: ClientsContainer = Container(  # type: ignore[assignment]
        ClientsContainer,
        config=config,
    )
    adapters: AdaptersContainer = Container(  # type: ignore[assignment]
        AdaptersContainer,
        clients=clients,
        config=config,
    )
    repositories: RepositoriesContainer = Container(  # type: ignore[assignment]
        RepositoriesContainer,
        adapters=adapters,
    )
    registries: RegistriesContainer = Container(  # type: ignore[assignment]
        RegistriesContainer,
        repositories=repositories,
    )
    utilities: UtilitiesContainer = Container(  # type: ignore[assignment]
        UtilitiesContainer
    )
    facilitators: FacilitatorsContainer = Container(  # type: ignore[assignment]
        FacilitatorsContainer,
        adapters=adapters,
        config=config,
    )
    transformers: TransformersContainer = Container(  # type: ignore[assignment]
        TransformersContainer
    )
    time_provider: TimeProviderContainer = Container(  # type: ignore[assignment]
        TimeProviderContainer
    )
    use_cases: UseCasesContainer = Container(  # type: ignore[assignment]
        UseCasesContainer,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
    )
    orchestrators: OrchestratorsContainer = Container(  # type: ignore[assignment]
        OrchestratorsContainer,
        use_cases=use_cases,
    )
    pipelines: PipelinesContainer = Container(  # type: ignore[assignment]
        PipelinesContainer,
        orchestrators=orchestrators,
    )
    operators: OperatorsContainer = Container(  # type: ignore[assignment]
        OperatorsContainer,
        pipelines=pipelines,
    )
    gateways: GatewaysContainer = Container(  # type: ignore[assignment]
        GatewaysContainer
    )
