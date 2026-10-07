from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.knowledge_pipelines import KnowledgePipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class KnowledgeOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of niche templates, the profile wizard, the knowledge
    base, menu import, resources and their schedule exceptions.
    """

    knowledge_pipelines: KnowledgePipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve.
    storage_scope = utilities.storage_scope

    # --- Niche templates and the profile wizard.
    list_niche_templates_operator = pipeline_operator(
        knowledge_pipelines.list_niche_templates_pipeline, storage_scope
    )
    get_niche_template_operator = pipeline_operator(
        knowledge_pipelines.get_niche_template_pipeline, storage_scope
    )
    get_profile_wizard_operator = pipeline_operator(
        knowledge_pipelines.get_profile_wizard_pipeline, storage_scope
    )
    get_business_profile_operator = pipeline_operator(
        knowledge_pipelines.get_business_profile_pipeline, storage_scope
    )
    save_profile_operator = pipeline_operator(
        knowledge_pipelines.save_profile_pipeline, storage_scope
    )
    save_profile_step_operator = pipeline_operator(
        knowledge_pipelines.save_profile_step_pipeline, storage_scope
    )
    compute_profile_gaps_operator = pipeline_operator(
        knowledge_pipelines.compute_profile_gaps_pipeline, storage_scope
    )

    # --- Knowledge base.
    list_knowledge_items_operator = pipeline_operator(
        knowledge_pipelines.list_knowledge_items_pipeline, storage_scope
    )
    create_knowledge_item_operator = pipeline_operator(
        knowledge_pipelines.create_knowledge_item_pipeline, storage_scope
    )
    get_knowledge_item_operator = pipeline_operator(
        knowledge_pipelines.get_knowledge_item_pipeline, storage_scope
    )
    update_knowledge_item_operator = pipeline_operator(
        knowledge_pipelines.update_knowledge_item_pipeline, storage_scope
    )
    delete_knowledge_item_operator = pipeline_operator(
        knowledge_pipelines.delete_knowledge_item_pipeline, storage_scope
    )
    search_knowledge_operator = pipeline_operator(
        knowledge_pipelines.search_knowledge_pipeline, storage_scope
    )

    # --- Resources and schedule exceptions.
    list_resources_operator = pipeline_operator(
        knowledge_pipelines.list_resources_pipeline, storage_scope
    )
    create_resource_operator = pipeline_operator(
        knowledge_pipelines.create_resource_pipeline, storage_scope
    )
    update_resource_operator = pipeline_operator(
        knowledge_pipelines.update_resource_pipeline, storage_scope
    )
    list_schedule_exceptions_operator = pipeline_operator(
        knowledge_pipelines.list_schedule_exceptions_pipeline, storage_scope
    )
    create_schedule_exception_operator = pipeline_operator(
        knowledge_pipelines.create_schedule_exception_pipeline, storage_scope
    )
    delete_schedule_exception_operator = pipeline_operator(
        knowledge_pipelines.delete_schedule_exception_pipeline, storage_scope
    )

    # --- Menu import.
    import_menu_operator = pipeline_operator(
        knowledge_pipelines.import_menu_pipeline, storage_scope
    )
    confirm_imported_items_operator = pipeline_operator(
        knowledge_pipelines.confirm_imported_items_pipeline, storage_scope
    )
    discard_import_batch_operator = pipeline_operator(
        knowledge_pipelines.discard_import_batch_pipeline, storage_scope
    )

    # --- Website import (the last one is the worker's job).
    start_website_import_operator = pipeline_operator(
        knowledge_pipelines.start_website_import_pipeline, storage_scope
    )
    get_website_import_operator = pipeline_operator(
        knowledge_pipelines.get_website_import_pipeline, storage_scope
    )
    run_website_import_operator = pipeline_operator(
        knowledge_pipelines.run_website_import_pipeline, storage_scope
    )
