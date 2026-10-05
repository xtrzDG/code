from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.orchestrators.conversation_orchestrators import (
    ConversationOrchestratorsContainer,
)
from app.containers.orchestrators.public_demo_orchestrators import (
    PublicDemoOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline
from app.containers.registries import RegistriesContainer
from app.contracts.pipeline_contract import PipelineContract
from app.pipelines.demo.public_demo_message_pipeline import PublicDemoMessagePipeline
from app.schemas.dto.public_demo import PublicDemoMessageCommand, PublicDemoReply


class PublicDemoPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of the landing page's sandbox demos: the list, and a visitor's
    message answered by the conversation turn in its own places.
    """

    public_demo_orchestrators: PublicDemoOrchestratorsContainer = (
        DependenciesContainer()
    )  # type: ignore[assignment]
    conversation_orchestrators: ConversationOrchestratorsContainer = (
        DependenciesContainer()  # type: ignore[assignment]
    )
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]

    list_public_demos_pipeline = orchestrator_pipeline(
        public_demo_orchestrators.list_public_demos_orchestrator
    )
    public_demo_message_pipeline: Factory[
        PipelineContract[PublicDemoMessageCommand, PublicDemoReply]
    ] = Factory(
        PublicDemoMessagePipeline,
        admit_message=public_demo_orchestrators.admit_public_demo_message_orchestrator,
        turn_orchestrator=conversation_orchestrators.conversation_turn_orchestrator,
        summarize_reply=public_demo_orchestrators.summarize_public_demo_reply_orchestrator,
        public_demo_slots=registries.public_demo_slots,
    )
