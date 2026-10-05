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
from app.containers.use_cases.booking_link_use_cases import (
    BookingLinkUseCasesContainer,
)
from app.containers.use_cases.booking_use_cases import BookingUseCasesContainer
from app.containers.use_cases.catalog_use_cases import CatalogUseCasesContainer
from app.containers.use_cases.compliance_use_cases import ComplianceUseCasesContainer
from app.containers.use_cases.customer_use_cases import CustomerUseCasesContainer
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.help_use_cases import HelpUseCasesContainer
from app.containers.use_cases.inbox_use_cases import InboxUseCasesContainer
from app.containers.use_cases.invoicing_use_cases import InvoicingUseCasesContainer
from app.containers.use_cases.knowledge_use_cases import KnowledgeUseCasesContainer
from app.containers.use_cases.legal_use_cases import LegalUseCasesContainer
from app.containers.use_cases.memory_use_cases import MemoryUseCasesContainer
from app.containers.use_cases.menu_import_use_cases import MenuImportUseCasesContainer
from app.containers.use_cases.mfa_use_cases import MfaUseCasesContainer
from app.containers.use_cases.privacy_use_cases import PrivacyUseCasesContainer
from app.containers.use_cases.public_demo_use_cases import (
    PublicDemoUseCasesContainer,
)
from app.containers.use_cases.reply_speed_use_cases import ReplySpeedUseCasesContainer
from app.containers.use_cases.scheduling_use_cases import SchedulingUseCasesContainer
from app.containers.use_cases.spend_guard_use_cases import SpendGuardUseCasesContainer
from app.containers.utilities import UtilitiesContainer


class CoreUseCasesContainer(containers.DeclarativeContainer):
    """
    The edges every use case context draws on and the contexts the others
    build on: accounts (and their two-factor sign-in), the catalog,
    compliance, invoicing, knowledge, menu import, scheduling, bookings, the
    team inbox, follow-ups, exports and reply speed. `UseCasesContainer` extends it
    with the contexts that depend on these and reads them as
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
    # The help center, support contacts and the guidance each person saw.
    help: HelpUseCasesContainer = Container(  # type: ignore[assignment]
        HelpUseCasesContainer,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
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
    # Legal texts, the sub-processor list and its change notices (1124).
    legal: LegalUseCasesContainer = Container(  # type: ignore[assignment]
        LegalUseCasesContainer,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The landing page's sandbox demos (PUBLIC_DEMO_BUSINESS_IDS).
    public_demos: PublicDemoUseCasesContainer = Container(  # type: ignore[assignment]
        PublicDemoUseCasesContainer,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
    # Billing details and the invoice and receipt PDFs (1114).
    invoicing: InvoicingUseCasesContainer = Container(  # type: ignore[assignment]
        InvoicingUseCasesContainer,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
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
    # The spend guard: spend limits, owner action and API limits, chat
    # websites, the platform's spend (1142).
    spend_guard: SpendGuardUseCasesContainer = Container(  # type: ignore[assignment]
        SpendGuardUseCasesContainer,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        account_use_cases=accounts,
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
    # A guest's booking page behind its manage link (/r/{token}).
    booking_links: BookingLinkUseCasesContainer = Container(  # type: ignore[assignment]
        BookingLinkUseCasesContainer,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        booking_use_cases=bookings,
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
    # Exports: the cabinet's tables as CSV, the full export of a business.
    privacy: PrivacyUseCasesContainer = Container(  # type: ignore[assignment]
        PrivacyUseCasesContainer,
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        account_use_cases=accounts,
    )
    # Customers' waits: grouped bursts, the turn deadline, measured replies.
    reply_speed: ReplySpeedUseCasesContainer = Container(  # type: ignore[assignment]
        ReplySpeedUseCasesContainer,
        config=config,
        facilitators=facilitators,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The customer memory: its settings and the conversation summaries (1121).
    memory: MemoryUseCasesContainer = Container(  # type: ignore[assignment]
        MemoryUseCasesContainer,
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        repositories=repositories,
        time_provider=time_provider,
        account_use_cases=accounts,
    )
    # Customers: the team's card, segments and the cabinet's search (1140).
    customers: CustomerUseCasesContainer = Container(  # type: ignore[assignment]
        CustomerUseCasesContainer,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        account_use_cases=accounts,
    )
