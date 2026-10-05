import sys

from dependency_injector import containers
from dependency_injector.providers import Container

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.adapters.analytics_collections_container import (
    AnalyticsCollectionsContainer,
)
from app.containers.adapters.client_care_collections_container import (
    ClientCareCollectionsContainer,
)
from app.containers.adapters.feedback_collections_container import (
    FeedbackCollectionsContainer,
)
from app.containers.adapters.inbox_collections_container import (
    InboxCollectionsContainer,
)
from app.containers.adapters.invoicing_collections_container import (
    InvoicingCollectionsContainer,
)
from app.containers.adapters.legal_collections_container import (
    LegalCollectionsContainer,
)
from app.containers.adapters.media_collections_container import (
    MediaCollectionsContainer,
)
from app.containers.adapters.operations_collections_container import (
    OperationsCollectionsContainer,
)
from app.containers.adapters.privacy_collections_container import (
    PrivacyCollectionsContainer,
)
from app.containers.adapters.rate_collections_container import (
    RateCollectionsContainer,
)
from app.containers.adapters.security_collections_container import (
    SecurityCollectionsContainer,
)
from app.containers.adapters.spend_guard_collections_container import (
    SpendGuardCollectionsContainer,
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
        UtilitiesContainer,
        config=config,
        time_provider=time_provider,
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
    # The growth analytics' collections (1074), one more sibling.
    analytics_collections: AnalyticsCollectionsContainer = Container(  # type: ignore[assignment]
        AnalyticsCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The collection of files customers send (1081), one more sibling.
    media_collections: MediaCollectionsContainer = Container(  # type: ignore[assignment]
        MediaCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The platform's alerts, backups and incidents (1093), one more sibling.
    operations_collections: OperationsCollectionsContainer = Container(  # type: ignore[assignment]
        OperationsCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The suppression list and the full business exports (1113), one more.
    privacy_collections: PrivacyCollectionsContainer = Container(  # type: ignore[assignment]
        PrivacyCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # Billing details and invoice numbers (1114), one more sibling.
    invoicing_collections: InvoicingCollectionsContainer = Container(  # type: ignore[assignment]
        InvoicingCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The sub-processor change notices (1124), one more sibling.
    legal_collections: LegalCollectionsContainer = Container(  # type: ignore[assignment]
        LegalCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # Spend limits and the websites allowed to show a chat (1142).
    spend_guard_collections: SpendGuardCollectionsContainer = Container(  # type: ignore[assignment]
        SpendGuardCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The admin's credit ledger, notes, health changes and digests (1143).
    client_care_collections: ClientCareCollectionsContainer = Container(  # type: ignore[assignment]
        ClientCareCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    repositories: RepositoriesContainer = Container(  # type: ignore[assignment]
        RepositoriesContainer,
        spend_guard_collections=spend_guard_collections,
        usage_collections=adapters.collections,
        client_care_collections=client_care_collections,
        growth_collections=adapters.growth_collections,
        legal_collections=legal_collections,
        privacy_collections=privacy_collections,
        retention_collections=adapters.collections,
        retention_call_adapters=adapters.calls,
        invoicing_collections=invoicing_collections,
        payment_collections=adapters.collections,
        operations_collections=operations_collections,
        health_collections=adapters.collections,
        media_collections=media_collections,
        rate_collections=rate_collections,
        analytics_collections=analytics_collections,
        inbox_collections=inbox_collections,
        customer_collections=adapters.collections,
        security_collections=security_collections,
        value_collections=value_collections,
        insight_collections=adapters.collections,
        feedback_collections=feedback_collections,
        collections=adapters.collections,
        notification_collections=adapters.notification_collections,
        launch_collections=adapters.launch_collections,
        probe_collections=adapters.collections,
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
        facilitators=facilitators,
        repositories=repositories,
        time_provider=time_provider,
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
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        operators=operators,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
