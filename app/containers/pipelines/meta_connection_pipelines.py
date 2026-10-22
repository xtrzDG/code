from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.meta_connection_orchestrators import (
    MetaConnectionOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class MetaConnectionPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of Meta's self-serve connection and comment-to-DM."""

    meta: MetaConnectionOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    sign_in_options_pipeline = orchestrator_pipeline(meta.sign_in_options_orchestrator)
    start_meta_connection_pipeline = orchestrator_pipeline(
        meta.start_meta_connection_orchestrator
    )
    complete_whatsapp_signup_pipeline = orchestrator_pipeline(
        meta.complete_whatsapp_signup_orchestrator
    )
    list_meta_pages_pipeline = orchestrator_pipeline(meta.list_meta_pages_orchestrator)
    connect_meta_page_pipeline = orchestrator_pipeline(
        meta.connect_meta_page_orchestrator
    )
    set_comment_replies_pipeline = orchestrator_pipeline(
        meta.set_comment_replies_orchestrator
    )
    process_comment_trigger_pipeline = orchestrator_pipeline(
        meta.process_comment_trigger_orchestrator
    )
