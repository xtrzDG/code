import sys

from dependency_injector.providers import Container

from app.containers.app_edges import AppEdgesContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.gateways import GatewaysContainer
from app.containers.operators.operators_container import OperatorsContainer
from app.containers.orchestrators.orchestrators_container import (
    OrchestratorsContainer,
)
from app.containers.pipelines.pipelines_container import PipelinesContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.use_cases_container import UseCasesContainer

# Building AppContainer deep-copies the whole provider graph (how
# dependency-injector instantiates a DeclarativeContainer), one Python frame
# per step of the deepest copy path. That path follows the copy order, which
# string hashing changes from process to process: the graph needs about 2,600
# to 2,900 frames (30 hash seeds measured), so the earlier 3,000 left a worker
# started under runpy too little room now and then. A process that builds the
# container gets more than three times the deepest path; recursion stays
# bounded, and tests/architecture_policy/test_container_build_headroom.py
# fails once the graph needs more than half of it.
CONTAINER_BUILD_RECURSION_LIMIT: int = 10_000
if sys.getrecursionlimit() < CONTAINER_BUILD_RECURSION_LIMIT:
    sys.setrecursionlimit(CONTAINER_BUILD_RECURSION_LIMIT)


class AppContainer(AppEdgesContainer):
    """
    The composition root of the API and the worker.

    Edges follow the role direction: operators -> pipelines -> orchestrators
    -> use cases -> repositories, registries, facilitators, transformers,
    utilities -> adapters -> clients. Tests override providers at the edges
    (settings, LLM adapter, external clients, OTP delivery).
    """

    repositories: RepositoriesContainer = Container(  # type: ignore[assignment]
        RepositoriesContainer,
        spend_guard_collections=AppEdgesContainer.spend_guard_collections,
        usage_collections=AppEdgesContainer.adapters.collections,
        client_care_collections=AppEdgesContainer.client_care_collections,
        referral_collections=AppEdgesContainer.client_care_collections,
        growth_collections=AppEdgesContainer.adapters.growth_collections,
        calendar_sync_collections=AppEdgesContainer.adapters.calendar_sync_collections,
        integration_collections=AppEdgesContainer.integration_collections,
        brand_collections=AppEdgesContainer.brand_collections,
        legal_collections=AppEdgesContainer.legal_collections,
        privacy_collections=AppEdgesContainer.privacy_collections,
        retention_collections=AppEdgesContainer.adapters.collections,
        retention_call_adapters=AppEdgesContainer.adapters.calls,
        invoicing_collections=AppEdgesContainer.invoicing_collections,
        payment_collections=AppEdgesContainer.adapters.collections,
        operations_collections=AppEdgesContainer.operations_collections,
        health_collections=AppEdgesContainer.adapters.collections,
        media_collections=AppEdgesContainer.media_collections,
        rate_collections=AppEdgesContainer.rate_collections,
        analytics_collections=AppEdgesContainer.analytics_collections,
        inbox_collections=AppEdgesContainer.inbox_collections,
        customer_collections=AppEdgesContainer.adapters.collections,
        security_collections=AppEdgesContainer.security_collections,
        value_collections=AppEdgesContainer.value_collections,
        insight_collections=AppEdgesContainer.adapters.collections,
        feedback_collections=AppEdgesContainer.feedback_collections,
        collections=AppEdgesContainer.adapters.collections,
        notification_collections=AppEdgesContainer.adapters.notification_collections,
        launch_collections=AppEdgesContainer.adapters.launch_collections,
        probe_collections=AppEdgesContainer.adapters.collections,
        call_adapters=AppEdgesContainer.adapters.calls,
        audit_chain_collections=AppEdgesContainer.audit_chain_collections,
        audit_entry_collections=AppEdgesContainer.adapters.collections,
        audit_adapters=AppEdgesContainer.adapters,
    )
    registries: RegistriesContainer = Container(  # type: ignore[assignment]
        RegistriesContainer,
        adapters=AppEdgesContainer.adapters,
        config=AppEdgesContainer.config,
        repositories=repositories,
        time_provider=AppEdgesContainer.time_provider,
    )
    transformers: TransformersContainer = Container(  # type: ignore[assignment]
        TransformersContainer,
        utilities=AppEdgesContainer.utilities,
    )
    facilitators: FacilitatorsContainer = Container(  # type: ignore[assignment]
        FacilitatorsContainer,
        adapters=AppEdgesContainer.adapters,
        clients=AppEdgesContainer.clients,
        config=AppEdgesContainer.config,
        registries=registries,
        repositories=repositories,
        time_provider=AppEdgesContainer.time_provider,
        transformers=transformers,
        utilities=AppEdgesContainer.utilities,
    )
    use_cases: UseCasesContainer = Container(  # type: ignore[assignment]
        UseCasesContainer,
        adapters=AppEdgesContainer.adapters,
        clients=AppEdgesContainer.clients,
        config=AppEdgesContainer.config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=AppEdgesContainer.time_provider,
        transformers=transformers,
        utilities=AppEdgesContainer.utilities,
    )
    orchestrators: OrchestratorsContainer = Container(  # type: ignore[assignment]
        OrchestratorsContainer,
        adapters=AppEdgesContainer.adapters,
        config=AppEdgesContainer.config,
        facilitators=facilitators,
        repositories=repositories,
        time_provider=AppEdgesContainer.time_provider,
        use_cases=use_cases,
        utilities=AppEdgesContainer.utilities,
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
        utilities=AppEdgesContainer.utilities,
        feedback_root=use_cases.feedback.root,
        passkey_root=use_cases.passkey_root,
    )
    gateways: GatewaysContainer = Container(  # type: ignore[assignment]
        GatewaysContainer,
        adapters=AppEdgesContainer.adapters,
        config=AppEdgesContainer.config,
        facilitators=facilitators,
        operators=operators,
        repositories=repositories,
        time_provider=AppEdgesContainer.time_provider,
        utilities=AppEdgesContainer.utilities,
    )
