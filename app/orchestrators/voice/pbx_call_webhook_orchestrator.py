from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.dto.calls.missed_calls import (
    MissedCallReport,
    PbxCallWebhookOutcome,
    PbxCallWebhookRequest,
    RegisteredMissedCall,
)


class PbxCallWebhookOrchestrator(
    OrchestratorContract[PbxCallWebhookRequest, PbxCallWebhookOutcome]
):
    """
    A notification of the telephony line (Zadarma PBX): check its
    signature, and for an incoming call the line did not put through
    (busy, no answer, the caller hung up first, a failed line) store the
    missed call, queue its text-back and tell staff. Other notifications,
    answered calls and lines no business has are ignored.
    """

    def __init__(
        self,
        read_pbx_missed_call: UseCaseContract[
            PbxCallWebhookRequest, MissedCallReport | None
        ],
        handle_missed_call: OrchestratorContract[
            MissedCallReport, RegisteredMissedCall | None
        ],
    ) -> None:
        self._read_pbx_missed_call: UseCaseContract[
            PbxCallWebhookRequest, MissedCallReport | None
        ] = read_pbx_missed_call
        self._handle_missed_call: OrchestratorContract[
            MissedCallReport, RegisteredMissedCall | None
        ] = handle_missed_call

    def execute(self, input_data: PbxCallWebhookRequest) -> PbxCallWebhookOutcome:
        report: MissedCallReport | None = self._read_pbx_missed_call.run(input_data)
        registered: RegisteredMissedCall | None = (
            None if report is None else self._handle_missed_call.execute(report)
        )
        if registered is None:
            return PbxCallWebhookOutcome(status=PostCallEventStatus.IGNORED)

        return PbxCallWebhookOutcome(
            status=(
                PostCallEventStatus.RECORDED
                if registered.is_new
                else PostCallEventStatus.DUPLICATE
            ),
            missed_call_id=registered.missed_call.id,
            text_back_status=registered.missed_call.status,
        )
