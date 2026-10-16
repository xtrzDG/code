from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.registries import CustomerMessageLockRegistryContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffCommand,
    WidgetHandoffView,
)
from app.schemas.typings.conversations.strings import ChannelUserId


class WidgetHandoffPipeline(PipelineContract[WidgetHandoffCommand, WidgetHandoffView]):
    """
    "Talk to a person" holds the visitor's customer lock, like their
    messages (`CustomerMessagePipeline`): a handoff never interleaves with
    a turn that is answering the same visitor, so the turn cannot store
    the conversation back over the handoff, and the next message sees it.
    """

    def __init__(
        self,
        widget_handoff_orchestrator: OrchestratorContract[
            WidgetHandoffCommand, WidgetHandoffView
        ],
        customer_locks: CustomerMessageLockRegistryContract,
    ) -> None:
        self._widget_handoff_orchestrator: OrchestratorContract[
            WidgetHandoffCommand, WidgetHandoffView
        ] = widget_handoff_orchestrator
        self._customer_locks: CustomerMessageLockRegistryContract = customer_locks

    def start(self, input_data: WidgetHandoffCommand) -> WidgetHandoffView:
        with self._customer_locks.lock_for_customer(
            input_data.business_id,
            ChannelKind.WEB_CHAT,
            ChannelUserId(str(input_data.request.session_key)),
        ):
            return self._widget_handoff_orchestrator.execute(input_data)
