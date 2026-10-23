from dependency_injector.providers import Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.meta_connection.meta_connection_dependencies import (
    MetaConnectionDependencies,
)
from app.containers.meta_connection.meta_connection_root import MetaConnectionRoot
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.delivery_use_cases import DeliveryUseCasesContainer
from app.containers.utilities import UtilitiesContainer


def meta_connection_root_provider(
    *,
    adapters: AdaptersContainer,
    clients: ClientsContainer,
    config: ConfigContainer,
    facilitators: FacilitatorsContainer,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    utilities: UtilitiesContainer,
    account_use_cases: AccountUseCasesContainer,
    delivery_use_cases: DeliveryUseCasesContainer,
) -> Singleton[MetaConnectionRoot]:
    """
    The root of Meta's self-serve connection (R15, migration 1212), its
    dependencies taken from the graph: the single seam between the providers
    and the typed root (app/containers/meta_connection/, ADR 0010; a missing
    or misspelt field fails test_every_provider_of_the_container_resolves).
    """

    return Singleton(
        MetaConnectionRoot,
        dependencies=Factory(
            MetaConnectionDependencies,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            step_up=utilities.step_up_guard,
            state_repo=repositories.meta_connection_state_repo,
            oauth_client=clients.meta_oauth_client,
            pages_client=clients.meta_pages_client,
            onboarding_client=clients.whatsapp_onboarding_client,
            meta_client=clients.meta_graph_client,
            instagram_adapter=adapters.instagram_channel_adapter,
            channel_repo=repositories.channel_repo,
            contact_repo=repositories.contact_repo,
            inbound_event_repo=repositories.inbound_event_repo,
            outbound_message_repo=repositories.outbound_message_repo,
            audit_log_repo=repositories.audit_log_repo,
            secret_cipher=adapters.secret_cipher,
            suppression_list=facilitators.suppression_list,
            job_queue=facilitators.job_queue_facilitator,
            rate_limit_registry=registries.request_rate_limit_registry,
            product_events=facilitators.product_events,
            claim_inbound_event=delivery_use_cases.claim_inbound_event_use_case,
            finish_inbound_event=delivery_use_cases.finish_inbound_event_use_case,
            release_inbound_event=delivery_use_cases.release_inbound_event_use_case,
            storage_scope=utilities.storage_scope,
            unit_of_work=adapters.storage_unit_of_work,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )
