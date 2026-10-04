from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.booking_use_cases import BookingUseCasesContainer
from app.containers.use_cases.catalog_use_cases import CatalogUseCasesContainer
from app.containers.use_cases.compliance_use_cases import ComplianceUseCasesContainer
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.inbox_use_cases import InboxUseCasesContainer
from app.containers.use_cases.knowledge_use_cases import KnowledgeUseCasesContainer
from app.containers.use_cases.menu_import_use_cases import MenuImportUseCasesContainer
from app.containers.use_cases.mfa_use_cases import MfaUseCasesContainer
from app.containers.use_cases.scheduling_use_cases import SchedulingUseCasesContainer
from app.containers.utilities import UtilitiesContainer


class CoreUseCasesContainer(containers.DeclarativeContainer):
    """
    The edges every use case context draws on and the contexts the others
    build on: accounts (and their two-factor sign-in), the catalog,
    compliance, knowledge, menu import,
    scheduling, bookings, the team inbox and follow-ups. `UseCasesContainer`
    extends it with the contexts that depend on these and reads them as
    `CoreUseCasesContainer.<name>`; one instance copies all of them
    together, so the overridden edges reach every context.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    accounts: AccountUseCasesContainer = Container(  # type: ignore[assignment]
        AccountUseCasesContainer,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
    )
    # Two-factor sign-in and step-up (accounts' send of login codes).
    mfa: MfaUseCasesContainer = Container(  # type: ignore[assignment]
        MfaUseCasesContainer,
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
        account_use_cases=accounts,
    )
    catalog: CatalogUseCasesContainer = Container(  # type: ignore[assignment]
        CatalogUseCasesContainer,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
    compliance: ComplianceUseCasesContainer = Container(  # type: ignore[assignment]
        ComplianceUseCasesContainer,
        facilitators=facilitators,
        adapters=adapters,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        account_use_cases=accounts,
    )
    knowledge: KnowledgeUseCasesContainer = Container(  # type: ignore[assignment]
        KnowledgeUseCasesContainer,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
    menu_import: MenuImportUseCasesContainer = Container(  # type: ignore[assignment]
        MenuImportUseCasesContainer,
        adapters=adapters,
        clients=clients,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        account_use_cases=accounts,
    )
    scheduling: SchedulingUseCasesContainer = Container(  # type: ignore[assignment]
        SchedulingUseCasesContainer,
        adapters=adapters,
        clients=clients,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
    )
    bookings: BookingUseCasesContainer = Container(  # type: ignore[assignment]
        BookingUseCasesContainer,
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
    )
    inbox: InboxUseCasesContainer = Container(  # type: ignore[assignment]
        InboxUseCasesContainer,
        facilitators=facilitators,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        account_use_cases=accounts,
    )
    follow_ups: FollowUpUseCasesContainer = Container(  # type: ignore[assignment]
        FollowUpUseCasesContainer,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
        inbox_use_cases=inbox,
    )
