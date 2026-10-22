from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.delivery_use_cases import DeliveryUseCasesContainer
from app.containers.use_cases.meta_connection_use_cases import (
    MetaConnectionUseCasesContainer,
)
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.channels.inbox.process_comment_trigger_orchestrator import (
    ProcessCommentTriggerOrchestrator,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput


class MetaConnectionOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of Meta's self-serve connection: one use case each for the
    cabinet, and the worker's private reply to a comment (the Meta webhook's
    intake of comments runs in `ChannelPipelinesContainer`).
    """

    meta_use_cases: MetaConnectionUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    delivery_use_cases: DeliveryUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    sign_in_options_orchestrator = use_case_orchestrator(
        meta_use_cases.get_meta_sign_in_options_use_case
    )
    start_meta_connection_orchestrator = use_case_orchestrator(
        meta_use_cases.start_meta_connection_use_case
    )
    complete_whatsapp_signup_orchestrator = use_case_orchestrator(
        meta_use_cases.complete_whatsapp_signup_use_case
    )
    list_meta_pages_orchestrator = use_case_orchestrator(
        meta_use_cases.list_meta_pages_use_case
    )
    connect_meta_page_orchestrator = use_case_orchestrator(
        meta_use_cases.connect_meta_page_use_case
    )
    set_comment_replies_orchestrator = use_case_orchestrator(
        meta_use_cases.set_comment_replies_use_case
    )
    process_comment_trigger_orchestrator: Factory[
        OrchestratorContract[QueuedJobInput, JobReport]
    ] = Factory(
        ProcessCommentTriggerOrchestrator,
        claim_inbound_event=delivery_use_cases.claim_inbound_event_use_case,
        reply_to_comment=meta_use_cases.reply_to_comment_trigger_use_case,
        finish_inbound_event=delivery_use_cases.finish_inbound_event_use_case,
        release_inbound_event=delivery_use_cases.release_inbound_event_use_case,
    )
