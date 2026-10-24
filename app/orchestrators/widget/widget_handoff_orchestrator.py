from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffCommand,
    WidgetHandoffNotice,
    WidgetHandoffTarget,
    WidgetHandoffView,
)
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult


class WidgetHandoffOrchestrator(
    OrchestratorContract[WidgetHandoffCommand, WidgetHandoffView]
):
    """
    "Talk to a person" in the website chat, or the widget giving up on an
    answer that never came: find (or open) the visitor's conversation,
    pass it to staff like the assistant's own handoff (notifications, the
    cabinet's queue, the assistant silent until staff close it), and tell
    the visitor in their language when they hear back. Asking again while
    staff have the conversation changes nothing and notifies nobody.
    """

    def __init__(
        self,
        open_widget_handoff: UseCaseContract[WidgetHandoffCommand, WidgetHandoffTarget],
        handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
        record_widget_handoff_notice: UseCaseContract[
            WidgetHandoffNotice, WidgetHandoffView
        ],
    ) -> None:
        self._open_widget_handoff: UseCaseContract[
            WidgetHandoffCommand, WidgetHandoffTarget
        ] = open_widget_handoff
        self._handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult] = (
            handoff_to_human
        )
        self._record_widget_handoff_notice: UseCaseContract[
            WidgetHandoffNotice, WidgetHandoffView
        ] = record_widget_handoff_notice

    def execute(self, input_data: WidgetHandoffCommand) -> WidgetHandoffView:
        target: WidgetHandoffTarget = self._open_widget_handoff.run(input_data)
        if target.is_already_handed_off:
            return self._record_widget_handoff_notice.run(
                WidgetHandoffNotice(
                    business_id=target.business_id,
                    conversation_id=target.conversation_id,
                    language=target.language,
                )
            )

        result: HandoffResult = self._handoff_to_human.run(
            HandoffCommand(
                business_id=target.business_id,
                conversation_id=target.conversation_id,
                contact_id=target.contact_id,
                reason=target.reason,
                summary=target.summary,
                urgency=target.urgency,
                source_channel=ChannelKind.WEB_CHAT,
                language=target.language,
            )
        )
        return self._record_widget_handoff_notice.run(
            WidgetHandoffNotice(
                business_id=target.business_id,
                conversation_id=target.conversation_id,
                text=result.customer_message,
                language=target.language,
            )
        )
