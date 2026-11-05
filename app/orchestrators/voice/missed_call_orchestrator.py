from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calls.missed_calls import MissedCallReport, RegisteredMissedCall
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)


class MissedCallOrchestrator(
    OrchestratorContract[MissedCallReport, RegisteredMissedCall | None]
):
    """
    A caller who never reached the phone assistant (the telephony line
    reported busy, no answer or a hang-up, or the voice platform could not
    start the call): store the missed call with its text-back, then tell
    staff so someone calls back. None when no business has the line.
    """

    def __init__(
        self,
        register_missed_call: UseCaseContract[
            MissedCallReport, RegisteredMissedCall | None
        ],
        notify_missed_call: UseCaseContract[
            RegisteredMissedCall | None, DeliveredNotificationCount
        ],
    ) -> None:
        self._register_missed_call: UseCaseContract[
            MissedCallReport, RegisteredMissedCall | None
        ] = register_missed_call
        self._notify_missed_call: UseCaseContract[
            RegisteredMissedCall | None, DeliveredNotificationCount
        ] = notify_missed_call

    def execute(self, input_data: MissedCallReport) -> RegisteredMissedCall | None:
        registered: RegisteredMissedCall | None = self._register_missed_call.run(
            input_data
        )
        self._notify_missed_call.run(registered)
        return registered
