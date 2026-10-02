from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.knowledge_use_cases import KnowledgeUseCasesContainer
from app.containers.use_cases.menu_import_use_cases import MenuImportUseCasesContainer
from app.containers.use_cases.scheduling_use_cases import SchedulingUseCasesContainer


class KnowledgeOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of niche templates, the profile wizard, the knowledge
    base, menu import, resources and their schedule exceptions.
    """

    knowledge_use_cases: KnowledgeUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    menu_import_use_cases: MenuImportUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    scheduling_use_cases: SchedulingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Niche templates and the profile wizard.
    list_niche_templates_orchestrator = use_case_orchestrator(
        knowledge_use_cases.list_niche_templates_use_case
    )
    get_niche_template_orchestrator = use_case_orchestrator(
        knowledge_use_cases.get_niche_template_use_case
    )
    get_profile_wizard_orchestrator = use_case_orchestrator(
        knowledge_use_cases.get_profile_wizard_use_case
    )
    get_business_profile_orchestrator = use_case_orchestrator(
        knowledge_use_cases.get_business_profile_use_case
    )
    save_profile_orchestrator = use_case_orchestrator(
        knowledge_use_cases.save_profile_use_case
    )
    save_profile_step_orchestrator = use_case_orchestrator(
        knowledge_use_cases.save_profile_step_use_case
    )
    compute_profile_gaps_orchestrator = use_case_orchestrator(
        knowledge_use_cases.compute_profile_gaps_use_case
    )

    # --- Knowledge base.
    list_knowledge_items_orchestrator = use_case_orchestrator(
        knowledge_use_cases.list_knowledge_items_use_case
    )
    create_knowledge_item_orchestrator = use_case_orchestrator(
        knowledge_use_cases.create_knowledge_item_use_case
    )
    get_knowledge_item_orchestrator = use_case_orchestrator(
        knowledge_use_cases.get_knowledge_item_use_case
    )
    update_knowledge_item_orchestrator = use_case_orchestrator(
        knowledge_use_cases.update_knowledge_item_use_case
    )
    delete_knowledge_item_orchestrator = use_case_orchestrator(
        knowledge_use_cases.delete_knowledge_item_use_case
    )
    search_knowledge_orchestrator = use_case_orchestrator(
        knowledge_use_cases.search_knowledge_use_case
    )

    # --- Resources and schedule exceptions.
    list_resources_orchestrator = use_case_orchestrator(
        scheduling_use_cases.list_resources_use_case
    )
    create_resource_orchestrator = use_case_orchestrator(
        scheduling_use_cases.create_resource_use_case
    )
    update_resource_orchestrator = use_case_orchestrator(
        scheduling_use_cases.update_resource_use_case
    )
    list_schedule_exceptions_orchestrator = use_case_orchestrator(
        scheduling_use_cases.list_schedule_exceptions_use_case
    )
    create_schedule_exception_orchestrator = use_case_orchestrator(
        scheduling_use_cases.create_schedule_exception_use_case
    )
    delete_schedule_exception_orchestrator = use_case_orchestrator(
        scheduling_use_cases.delete_schedule_exception_use_case
    )

    # --- Menu import.
    import_menu_orchestrator = use_case_orchestrator(
        menu_import_use_cases.import_menu_use_case
    )
    confirm_imported_items_orchestrator = use_case_orchestrator(
        menu_import_use_cases.confirm_imported_items_use_case
    )
    discard_import_batch_orchestrator = use_case_orchestrator(
        menu_import_use_cases.discard_import_batch_use_case
    )
