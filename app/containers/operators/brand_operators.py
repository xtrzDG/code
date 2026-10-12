from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.brand_pipelines import BrandPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class BrandOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of brands (1192). A brand request names no business, so it
    runs unscoped: it reaches only platform collections (brands,
    businesses, users, the audit log) until a step enters a location's
    own scope. Leaving a brand and overriding a shared fact are a
    location's own routes and run in its scope.
    """

    brand_pipelines: BrandPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope
    pipelines = brand_pipelines

    list_my_brands_operator = pipeline_operator(
        pipelines.list_my_brands_pipeline, storage_scope
    )
    get_brand_operator = pipeline_operator(pipelines.get_brand_pipeline, storage_scope)
    create_brand_operator = pipeline_operator(
        pipelines.create_brand_pipeline, storage_scope
    )
    rename_brand_operator = pipeline_operator(
        pipelines.rename_brand_pipeline, storage_scope
    )
    delete_brand_operator = pipeline_operator(
        pipelines.delete_brand_pipeline, storage_scope
    )
    get_brand_dashboard_operator = pipeline_operator(
        pipelines.get_brand_dashboard_pipeline, storage_scope
    )
    add_brand_location_operator = pipeline_operator(
        pipelines.add_brand_location_pipeline, storage_scope
    )
    remove_brand_location_operator = pipeline_operator(
        pipelines.remove_brand_location_pipeline, storage_scope
    )
    clone_brand_location_operator = pipeline_operator(
        pipelines.clone_brand_location_pipeline, storage_scope
    )
    leave_brand_operator = pipeline_operator(
        pipelines.leave_brand_pipeline, storage_scope
    )
    invite_brand_member_operator = pipeline_operator(
        pipelines.invite_brand_member_pipeline, storage_scope
    )
    change_brand_member_operator = pipeline_operator(
        pipelines.change_brand_member_pipeline, storage_scope
    )
    remove_brand_member_operator = pipeline_operator(
        pipelines.remove_brand_member_pipeline, storage_scope
    )
    list_brand_knowledge_operator = pipeline_operator(
        pipelines.list_brand_knowledge_pipeline, storage_scope
    )
    create_brand_knowledge_item_operator = pipeline_operator(
        pipelines.create_brand_knowledge_item_pipeline, storage_scope
    )
    update_brand_knowledge_item_operator = pipeline_operator(
        pipelines.update_brand_knowledge_item_pipeline, storage_scope
    )
    delete_brand_knowledge_item_operator = pipeline_operator(
        pipelines.delete_brand_knowledge_item_pipeline, storage_scope
    )
    override_brand_knowledge_operator = pipeline_operator(
        pipelines.override_brand_knowledge_pipeline, storage_scope
    )
