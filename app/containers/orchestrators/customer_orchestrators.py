from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.customer_use_cases import CustomerUseCasesContainer


class CustomerOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of Customers and the cabinet's search (one use case each)."""

    customer_use_cases: CustomerUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    change_customer_card_orchestrator = use_case_orchestrator(
        customer_use_cases.change_customer_card_use_case
    )
    change_customer_blocking_orchestrator = use_case_orchestrator(
        customer_use_cases.change_customer_blocking_use_case
    )
    get_contact_standing_orchestrator = use_case_orchestrator(
        customer_use_cases.get_contact_standing_use_case
    )
    get_customer_settings_orchestrator = use_case_orchestrator(
        customer_use_cases.get_customer_settings_use_case
    )
    update_customer_settings_orchestrator = use_case_orchestrator(
        customer_use_cases.update_customer_settings_use_case
    )
    list_segments_orchestrator = use_case_orchestrator(
        customer_use_cases.list_segments_use_case
    )
    create_segment_orchestrator = use_case_orchestrator(
        customer_use_cases.create_segment_use_case
    )
    update_segment_orchestrator = use_case_orchestrator(
        customer_use_cases.update_segment_use_case
    )
    delete_segment_orchestrator = use_case_orchestrator(
        customer_use_cases.delete_segment_use_case
    )
    list_segment_members_orchestrator = use_case_orchestrator(
        customer_use_cases.list_segment_members_use_case
    )
    preview_segment_orchestrator = use_case_orchestrator(
        customer_use_cases.preview_segment_use_case
    )
    start_segment_export_orchestrator = use_case_orchestrator(
        customer_use_cases.start_segment_export_use_case
    )
    read_segment_export_page_orchestrator = use_case_orchestrator(
        customer_use_cases.read_segment_export_page_use_case
    )
    search_business_orchestrator = use_case_orchestrator(
        customer_use_cases.search_business_use_case
    )
