from typed_time_provider import Microseconds, WallClock

from app.contracts.telephony import PbxWebhookAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calls.missed_calls import MissedCallReport, PbxCallWebhookRequest


class ReadPbxMissedCallUseCase(
    UseCaseContract[PbxCallWebhookRequest, MissedCallReport | None]
):
    """
    Check the signature of a telephony line notification (the platform's
    Zadarma API secret) and read the caller who did not get through; None
    for other notifications and answered calls.
    """

    def __init__(
        self,
        pbx_webhook_adapter: PbxWebhookAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._pbx_webhook_adapter: PbxWebhookAdapterContract = pbx_webhook_adapter
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PbxCallWebhookRequest) -> MissedCallReport | None:
        self._pbx_webhook_adapter.verify_signature(input_data)
        return self._pbx_webhook_adapter.parse_missed_call(
            input_data, self._wall_clock.now_unix()
        )
