from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.brand_orchestrators import (
    BrandOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class BrandPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of brands (1192): one orchestrator each."""

    brands: BrandOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    list_my_brands_pipeline = orchestrator_pipeline(brands.list_my_brands_orchestrator)
    get_brand_pipeline = orchestrator_pipeline(brands.get_brand_orchestrator)
    create_brand_pipeline = orchestrator_pipeline(brands.create_brand_orchestrator)
    rename_brand_pipeline = orchestrator_pipeline(brands.rename_brand_orchestrator)
    delete_brand_pipeline = orchestrator_pipeline(brands.delete_brand_orchestrator)
    get_brand_dashboard_pipeline = orchestrator_pipeline(
        brands.get_brand_dashboard_orchestrator
    )
    add_brand_location_pipeline = orchestrator_pipeline(
        brands.add_brand_location_orchestrator
    )
    remove_brand_location_pipeline = orchestrator_pipeline(
        brands.remove_brand_location_orchestrator
    )
    clone_brand_location_pipeline = orchestrator_pipeline(
        brands.clone_brand_location_orchestrator
    )
    leave_brand_pipeline = orchestrator_pipeline(brands.leave_brand_orchestrator)
    invite_brand_member_pipeline = orchestrator_pipeline(
        brands.invite_brand_member_orchestrator
    )
    change_brand_member_pipeline = orchestrator_pipeline(
        brands.change_brand_member_orchestrator
    )
    remove_brand_member_pipeline = orchestrator_pipeline(
        brands.remove_brand_member_orchestrator
    )
    list_brand_knowledge_pipeline = orchestrator_pipeline(
        brands.list_brand_knowledge_orchestrator
    )
    create_brand_knowledge_item_pipeline = orchestrator_pipeline(
        brands.create_brand_knowledge_item_orchestrator
    )
    update_brand_knowledge_item_pipeline = orchestrator_pipeline(
        brands.update_brand_knowledge_item_orchestrator
    )
    delete_brand_knowledge_item_pipeline = orchestrator_pipeline(
        brands.delete_brand_knowledge_item_orchestrator
    )
    override_brand_knowledge_pipeline = orchestrator_pipeline(
        brands.override_brand_knowledge_orchestrator
    )
    list_location_shared_knowledge_pipeline = orchestrator_pipeline(
        brands.list_location_shared_knowledge_orchestrator
    )
    quote_location_plans_pipeline = orchestrator_pipeline(
        brands.quote_location_plans_orchestrator
    )
