from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calls.call_fallback import (
    CallFallbackPlan,
    CallFallbackReply,
    CallFallbackWebhookRequest,
)
from app.schemas.dto.calls.missed_calls import MissedCallReport, RegisteredMissedCall
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)


class CallFallbackOrchestrator(
    OrchestratorContract[CallFallbackWebhookRequest, CallFallbackReply]
):
    """
    A call the voice platform could not take, as the carrier's fallback
    asks about it: put the caller through to the staff mobile on duty (or
    store the missed call with its text-back when nobody can take it),
    tell the owner, and answer the carrier what to do with the call.
    """

    def __init__(
        self,
        route_call_fallback: UseCaseContract[
            CallFallbackWebhookRequest, CallFallbackPlan
        ],
        notify_call_fallback: UseCaseContract[
            CallFallbackPlan, DeliveredNotificationCount
        ],
        handle_missed_call: OrchestratorContract[
            MissedCallReport, RegisteredMissedCall | None
        ],
    ) -> None:
        self._route_call_fallback: UseCaseContract[
            CallFallbackWebhookRequest, CallFallbackPlan
        ] = route_call_fallback
        self._notify_call_fallback: UseCaseContract[
            CallFallbackPlan, DeliveredNotificationCount
        ] = notify_call_fallback
        self._handle_missed_call: OrchestratorContract[
            MissedCallReport, RegisteredMissedCall | None
        ] = handle_missed_call

    def execute(self, input_data: CallFallbackWebhookRequest) -> CallFallbackReply:
        plan: CallFallbackPlan = self._route_call_fallback.run(input_data)
        if plan.missed_call is not None:
            self._handle_missed_call.execute(plan.missed_call)

        self._notify_call_fallback.run(plan)
        return plan.reply
