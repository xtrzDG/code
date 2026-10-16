from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.customer_pipelines import CustomerPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class CustomerOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of Customers and the cabinet's search, each in the scope of
    the business its input names.
    """

    customer_pipelines: CustomerPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    change_customer_card_operator = pipeline_operator(
        customer_pipelines.change_customer_card_pipeline, storage_scope
    )
    change_customer_blocking_operator = pipeline_operator(
        customer_pipelines.change_customer_blocking_pipeline, storage_scope
    )
    get_contact_standing_operator = pipeline_operator(
        customer_pipelines.get_contact_standing_pipeline, storage_scope
    )
    get_customer_settings_operator = pipeline_operator(
        customer_pipelines.get_customer_settings_pipeline, storage_scope
    )
    update_customer_settings_operator = pipeline_operator(
        customer_pipelines.update_customer_settings_pipeline, storage_scope
    )
    list_segments_operator = pipeline_operator(
        customer_pipelines.list_segments_pipeline, storage_scope
    )
    create_segment_operator = pipeline_operator(
        customer_pipelines.create_segment_pipeline, storage_scope
    )
    update_segment_operator = pipeline_operator(
        customer_pipelines.update_segment_pipeline, storage_scope
    )
    delete_segment_operator = pipeline_operator(
        customer_pipelines.delete_segment_pipeline, storage_scope
    )
    list_segment_members_operator = pipeline_operator(
        customer_pipelines.list_segment_members_pipeline, storage_scope
    )
    preview_segment_operator = pipeline_operator(
        customer_pipelines.preview_segment_pipeline, storage_scope
    )
    start_segment_export_operator = pipeline_operator(
        customer_pipelines.start_segment_export_pipeline, storage_scope
    )
    read_segment_export_page_operator = pipeline_operator(
        customer_pipelines.read_segment_export_page_pipeline, storage_scope
    )
    search_business_operator = pipeline_operator(
        customer_pipelines.search_business_pipeline, storage_scope
    )
