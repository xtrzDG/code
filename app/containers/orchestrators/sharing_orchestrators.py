from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.sharing_use_cases import SharingUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.sharing.hosted_chat_orchestrator import HostedChatOrchestrator
from app.orchestrators.widget.widget_handoff_orchestrator import (
    WidgetHandoffOrchestrator,
)
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffCommand,
    WidgetHandoffView,
)
from app.schemas.dto.sharing import HostedChatLookup, HostedChatView


class SharingOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of sharing the assistant: the share links and address
    (one use case each), the hosted chat page (find the business, then read
    in its scope) and the widget's "Talk to a person".
    """

    sharing_use_cases: SharingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    follow_up_use_cases: FollowUpUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_share_links_orchestrator = use_case_orchestrator(
        sharing_use_cases.get_share_links_use_case
    )
    set_public_slug_orchestrator = use_case_orchestrator(
        sharing_use_cases.set_public_slug_use_case
    )
    hosted_chat_orchestrator: Factory[
        OrchestratorContract[HostedChatLookup, HostedChatView]
    ] = Factory(
        HostedChatOrchestrator,
        resolve_hosted_chat=sharing_use_cases.resolve_hosted_chat_use_case,
        get_hosted_chat=sharing_use_cases.get_hosted_chat_use_case,
        storage_scope=utilities.storage_scope,
    )
    widget_handoff_orchestrator: Factory[
        OrchestratorContract[WidgetHandoffCommand, WidgetHandoffView]
    ] = Factory(
        WidgetHandoffOrchestrator,
        open_widget_handoff=sharing_use_cases.open_widget_handoff_use_case,
        handoff_to_human=follow_up_use_cases.handoff_to_human_use_case,
        record_widget_handoff_notice=(
            sharing_use_cases.record_widget_handoff_notice_use_case
        ),
    )
    open_widget_stream_orchestrator = use_case_orchestrator(
        sharing_use_cases.open_widget_stream_use_case
    )
    read_widget_stream_message_orchestrator = use_case_orchestrator(
        sharing_use_cases.read_widget_stream_message_use_case
    )
