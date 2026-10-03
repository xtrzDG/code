import sys

from dependency_injector import containers
from dependency_injector.providers import Container

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.adapters.feedback_collections_container import (
    FeedbackCollectionsContainer,
)
from app.containers.adapters.inbox_collections_container import (
    InboxCollectionsContainer,
)
from app.containers.adapters.rate_collections_container import (
    RateCollectionsContainer,
)
from app.containers.adapters.security_collections_container import (
    SecurityCollectionsContainer,
)
from app.containers.adapters.value_collections_container import (
    ValueCollectionsContainer,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.gateways import GatewaysContainer
from app.containers.operators.operators_container import OperatorsContainer
from app.containers.orchestrators.orchestrators_container import (
    OrchestratorsContainer,
)
from app.containers.pipelines.pipelines_container import PipelinesContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.use_cases_container import UseCasesContainer
from app.containers.utilities import UtilitiesContainer

# Building AppContainer deep-copies the whole provider graph (how
# dependency-injector instantiates a DeclarativeContainer), one Python frame
# per edge of the deepest copy path: about 925 frames for this graph, too
# close to CPython's default limit of 1000 once a server's or a test
# runner's own frames sit below it. A process that builds the container gets
# headroom; recursion stays bounded.
CONTAINER_BUILD_RECURSION_LIMIT: int = 3000
if sys.getrecursionlimit() < CONTAINER_BUILD_RECURSION_LIMIT:
    sys.setrecursionlimit(CONTAINER_BUILD_RECURSION_LIMIT)


class AppContainer(containers.DeclarativeContainer):
    """
    The composition root of the API and the worker.

    Edges follow the role direction: operators -> pipelines -> orchestrators
    -> use cases -> repositories, registries, facilitators, transformers,
    utilities -> adapters -> clients. Tests override providers at the edges
    (settings, LLM adapter, external clients, OTP delivery).
    """

    config: ConfigContainer = Container(ConfigContainer)  # type: ignore[assignment]
    time_provider: TimeProviderContainer = Container(  # type: ignore[assignment]
        TimeProviderContainer
    )
    utilities: UtilitiesContainer = Container(  # type: ignore[assignment]
        UtilitiesContainer
    )
    clients: ClientsContainer = Container(  # type: ignore[assignment]
        ClientsContainer,
        config=config,
    )
    adapters: AdaptersContainer = Container(  # type: ignore[assignment]
        AdaptersContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The team inbox's collections (1053), a sibling of the adapters' own.
    inbox_collections: InboxCollectionsContainer = Container(  # type: ignore[assignment]
        InboxCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # Key management's collection (1063), a sibling as well.
    security_collections: SecurityCollectionsContainer = Container(  # type: ignore[assignment]
        SecurityCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # What the assistant is worth: average check, digests, reports (1061).
    value_collections: ValueCollectionsContainer = Container(  # type: ignore[assignment]
        ValueCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The feedback after visits' collections (1062), another sibling.
    feedback_collections: FeedbackCollectionsContainer = Container(  # type: ignore[assignment]
        FeedbackCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The dated exchange rates' collection (1071), a sibling as well.
    rate_collections: RateCollectionsContainer = Container(  # type: ignore[assignment]
        RateCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    repositories: RepositoriesContainer = Container(  # type: ignore[assignment]
        RepositoriesContainer,
        rate_collections=rate_collections,
        inbox_collections=inbox_collections,
        security_collections=security_collections,
        value_collections=value_collections,
        feedback_collections=feedback_collections,
        collections=adapters.collections,
        notification_collections=adapters.notification_collections,
        launch_collections=adapters.launch_collections,
        call_adapters=adapters.calls,
    )
    registries: RegistriesContainer = Container(  # type: ignore[assignment]
        RegistriesContainer,
        adapters=adapters,
        config=config,
        repositories=repositories,
        time_provider=time_provider,
    )
    transformers: TransformersContainer = Container(  # type: ignore[assignment]
        TransformersContainer,
        utilities=utilities,
    )
    facilitators: FacilitatorsContainer = Container(  # type: ignore[assignment]
        FacilitatorsContainer,
        adapters=adapters,
        clients=clients,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
    )
    use_cases: UseCasesContainer = Container(  # type: ignore[assignment]
        UseCasesContainer,
        adapters=adapters,
        clients=clients,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
    )
    orchestrators: OrchestratorsContainer = Container(  # type: ignore[assignment]
        OrchestratorsContainer,
        adapters=adapters,
        config=config,
        repositories=repositories,
        use_cases=use_cases,
        utilities=utilities,
    )
    pipelines: PipelinesContainer = Container(  # type: ignore[assignment]
        PipelinesContainer,
        orchestrators=orchestrators,
        registries=registries,
        use_cases=use_cases,
    )
    operators: OperatorsContainer = Container(  # type: ignore[assignment]
        OperatorsContainer,
        pipelines=pipelines,
        utilities=utilities,
    )
    gateways: GatewaysContainer = Container(  # type: ignore[assignment]
        GatewaysContainer,
        config=config,
        facilitators=facilitators,
        operators=operators,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
