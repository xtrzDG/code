from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.customer_orchestrators import (
    CustomerOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class CustomerPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of Customers and the cabinet's search."""

    customers: CustomerOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    change_customer_card_pipeline = orchestrator_pipeline(
        customers.change_customer_card_orchestrator
    )
    change_customer_blocking_pipeline = orchestrator_pipeline(
        customers.change_customer_blocking_orchestrator
    )
    get_contact_standing_pipeline = orchestrator_pipeline(
        customers.get_contact_standing_orchestrator
    )
    get_customer_settings_pipeline = orchestrator_pipeline(
        customers.get_customer_settings_orchestrator
    )
    update_customer_settings_pipeline = orchestrator_pipeline(
        customers.update_customer_settings_orchestrator
    )
    list_segments_pipeline = orchestrator_pipeline(customers.list_segments_orchestrator)
    create_segment_pipeline = orchestrator_pipeline(
        customers.create_segment_orchestrator
    )
    update_segment_pipeline = orchestrator_pipeline(
        customers.update_segment_orchestrator
    )
    delete_segment_pipeline = orchestrator_pipeline(
        customers.delete_segment_orchestrator
    )
    list_segment_members_pipeline = orchestrator_pipeline(
        customers.list_segment_members_orchestrator
    )
    preview_segment_pipeline = orchestrator_pipeline(
        customers.preview_segment_orchestrator
    )
    start_segment_export_pipeline = orchestrator_pipeline(
        customers.start_segment_export_orchestrator
    )
    read_segment_export_page_pipeline = orchestrator_pipeline(
        customers.read_segment_export_page_orchestrator
    )
    search_business_pipeline = orchestrator_pipeline(
        customers.search_business_orchestrator
    )
