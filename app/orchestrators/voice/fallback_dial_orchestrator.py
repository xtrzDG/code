from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calls.call_fallback import (
    CallFallbackReply,
    CallFallbackWebhookRequest,
    FallbackDialOutcome,
)
from app.schemas.dto.calls.missed_calls import MissedCallReport, RegisteredMissedCall


class FallbackDialOrchestrator(
    OrchestratorContract[CallFallbackWebhookRequest, CallFallbackReply]
):
    """
    How the call the fallback put through to the staff mobile ended: when
    nobody took it, the caller is a missed call with its text-back and
    staff are told to call back; then the call ends.
    """

    def __init__(
        self,
        read_fallback_dial: UseCaseContract[
            CallFallbackWebhookRequest, FallbackDialOutcome
        ],
        handle_missed_call: OrchestratorContract[
            MissedCallReport, RegisteredMissedCall | None
        ],
    ) -> None:
        self._read_fallback_dial: UseCaseContract[
            CallFallbackWebhookRequest, FallbackDialOutcome
        ] = read_fallback_dial
        self._handle_missed_call: OrchestratorContract[
            MissedCallReport, RegisteredMissedCall | None
        ] = handle_missed_call

    def execute(self, input_data: CallFallbackWebhookRequest) -> CallFallbackReply:
        outcome: FallbackDialOutcome = self._read_fallback_dial.run(input_data)
        if outcome.missed_call is not None:
            self._handle_missed_call.execute(outcome.missed_call)

        return outcome.reply
