from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.brand_use_cases import BrandUseCasesContainer
from app.containers.use_cases.catalog_use_cases import CatalogUseCasesContainer
from app.containers.use_cases.inbox_use_cases import InboxUseCasesContainer
from app.containers.use_cases.value_use_cases import ValueUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.brands.brand_dashboard_orchestrator import (
    BrandDashboardOrchestrator,
)
from app.orchestrators.brands.brand_knowledge_orchestrator import (
    BrandKnowledgeOrchestrator,
)
from app.orchestrators.brands.clone_brand_location_orchestrator import (
    CloneBrandLocationOrchestrator,
)
from app.orchestrators.brands.location_plan_quotes_orchestrator import (
    LocationPlanQuotesOrchestrator,
)
from app.schemas.dto.brands.brand_commands import BrandQuery, CloneBrandLocationCommand
from app.schemas.dto.brands.brand_dashboard import BrandDashboard, BrandDashboardQuery
from app.schemas.dto.brands.brand_knowledge import BrandKnowledgeList
from app.schemas.dto.brands.location_plans import (
    LocationPlanQuery,
    LocationPlanQuoteList,
)
from app.schemas.dto.businesses import BusinessView


class BrandOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of brands (1192): one use case each, but the combined
    dashboard, the shared knowledge with its overrides and "New location
    from…", which read and write each location inside its own scope.
    """

    brand_use_cases: BrandUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    value_use_cases: ValueUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    inbox_use_cases: InboxUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    catalog_use_cases: CatalogUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    cases = brand_use_cases

    list_my_brands_orchestrator = use_case_orchestrator(cases.list_my_brands_use_case)
    get_brand_orchestrator = use_case_orchestrator(cases.get_brand_use_case)
    create_brand_orchestrator = use_case_orchestrator(cases.create_brand_use_case)
    rename_brand_orchestrator = use_case_orchestrator(cases.rename_brand_use_case)
    delete_brand_orchestrator = use_case_orchestrator(cases.delete_brand_use_case)
    add_brand_location_orchestrator = use_case_orchestrator(
        cases.add_brand_location_use_case
    )
    remove_brand_location_orchestrator = use_case_orchestrator(
        cases.remove_brand_location_use_case
    )
    leave_brand_orchestrator = use_case_orchestrator(cases.leave_brand_use_case)
    invite_brand_member_orchestrator = use_case_orchestrator(
        cases.invite_brand_member_use_case
    )
    change_brand_member_orchestrator = use_case_orchestrator(
        cases.change_brand_member_use_case
    )
    remove_brand_member_orchestrator = use_case_orchestrator(
        cases.remove_brand_member_use_case
    )
    create_brand_knowledge_item_orchestrator = use_case_orchestrator(
        cases.create_brand_knowledge_item_use_case
    )
    update_brand_knowledge_item_orchestrator = use_case_orchestrator(
        cases.update_brand_knowledge_item_use_case
    )
    delete_brand_knowledge_item_orchestrator = use_case_orchestrator(
        cases.delete_brand_knowledge_item_use_case
    )
    override_brand_knowledge_orchestrator = use_case_orchestrator(
        cases.override_brand_knowledge_use_case
    )
    list_location_shared_knowledge_orchestrator = use_case_orchestrator(
        cases.list_location_shared_knowledge_use_case
    )
    quote_location_plans_orchestrator: Factory[
        OrchestratorContract[LocationPlanQuery, LocationPlanQuoteList]
    ] = Factory(
        LocationPlanQuotesOrchestrator,
        describe_pricing=cases.describe_location_pricing_use_case,
        quote_plans=catalog_use_cases.quote_plans_use_case,
    )
    get_brand_dashboard_orchestrator: Factory[
        OrchestratorContract[BrandDashboardQuery, BrandDashboard]
    ] = Factory(
        BrandDashboardOrchestrator,
        get_brand=cases.get_brand_use_case,
        get_value=value_use_cases.get_business_value_use_case,
        get_sources=value_use_cases.get_customer_sources_use_case,
        count_inbox=inbox_use_cases.count_inbox_attention_use_case,
        storage_scope=utilities.storage_scope,
    )
    list_brand_knowledge_orchestrator: Factory[
        OrchestratorContract[BrandQuery, BrandKnowledgeList]
    ] = Factory(
        BrandKnowledgeOrchestrator,
        get_brand=cases.get_brand_use_case,
        list_knowledge=cases.list_brand_knowledge_use_case,
        list_overrides=cases.list_location_overrides_use_case,
        storage_scope=utilities.storage_scope,
    )
    clone_brand_location_orchestrator: Factory[
        OrchestratorContract[CloneBrandLocationCommand, BusinessView]
    ] = Factory(
        CloneBrandLocationOrchestrator,
        authorize_clone=cases.authorize_location_clone_use_case,
        read_template=cases.read_location_template_use_case,
        create_location=cases.create_cloned_location_use_case,
        write_template=cases.write_location_template_use_case,
        get_business=account_use_cases.get_business_use_case,
        storage_scope=utilities.storage_scope,
    )
