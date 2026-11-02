from typed_time_provider import Microseconds, WallClock

from app.contracts.telephony import CallFallbackAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calls.call_fallback import (
    CallFallbackWebhookRequest,
    FallbackDialOutcome,
    FallbackDialReport,
)


class ReadFallbackDialUseCase(
    UseCaseContract[CallFallbackWebhookRequest, FallbackDialOutcome]
):
    """
    Check the carrier's signature on how the call put through to the staff
    mobile ended: a mobile that was busy, rang out or failed (or a caller
    who hung up while it rang) leaves a missed call of the line with its
    text-back. Either way the call ends there. A signed copy of a report
    already handled changes nothing and is answered with nothing.
    """

    def __init__(
        self,
        call_fallback_adapter: CallFallbackAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._call_fallback_adapter: CallFallbackAdapterContract = call_fallback_adapter
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CallFallbackWebhookRequest) -> FallbackDialOutcome:
        report: FallbackDialReport = self._call_fallback_adapter.read_dial_outcome(
            input_data, self._wall_clock.now_unix()
        )
        if report.is_repeated:
            return FallbackDialOutcome(
                reply=self._call_fallback_adapter.ignore_request()
            )

        return FallbackDialOutcome(
            missed_call=report.missed_call,
            reply=self._call_fallback_adapter.end_call(),
        )
