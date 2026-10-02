from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.knowledge_orchestrators import (
    KnowledgeOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class KnowledgePipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of niche templates, the profile wizard, the knowledge
    base, menu import, resources and their schedule exceptions.
    """

    knowledge_orchestrators: KnowledgeOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Niche templates and the profile wizard.
    list_niche_templates_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.list_niche_templates_orchestrator
    )
    get_niche_template_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.get_niche_template_orchestrator
    )
    get_profile_wizard_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.get_profile_wizard_orchestrator
    )
    get_business_profile_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.get_business_profile_orchestrator
    )
    save_profile_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.save_profile_orchestrator
    )
    save_profile_step_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.save_profile_step_orchestrator
    )
    compute_profile_gaps_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.compute_profile_gaps_orchestrator
    )

    # --- Knowledge base.
    list_knowledge_items_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.list_knowledge_items_orchestrator
    )
    create_knowledge_item_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.create_knowledge_item_orchestrator
    )
    get_knowledge_item_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.get_knowledge_item_orchestrator
    )
    update_knowledge_item_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.update_knowledge_item_orchestrator
    )
    delete_knowledge_item_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.delete_knowledge_item_orchestrator
    )
    search_knowledge_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.search_knowledge_orchestrator
    )

    # --- Resources and schedule exceptions.
    list_resources_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.list_resources_orchestrator
    )
    create_resource_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.create_resource_orchestrator
    )
    update_resource_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.update_resource_orchestrator
    )
    list_schedule_exceptions_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.list_schedule_exceptions_orchestrator
    )
    create_schedule_exception_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.create_schedule_exception_orchestrator
    )
    delete_schedule_exception_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.delete_schedule_exception_orchestrator
    )

    # --- Menu import.
    import_menu_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.import_menu_orchestrator
    )
    confirm_imported_items_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.confirm_imported_items_orchestrator
    )
    discard_import_batch_pipeline = orchestrator_pipeline(
        knowledge_orchestrators.discard_import_batch_orchestrator
    )
