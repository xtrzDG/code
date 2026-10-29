from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import VoiceWebhookAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.dto.voice_webhooks import PostCallWebhookRequest


class ReadFailedCallStartUseCase(
    UseCaseContract[PostCallWebhookRequest, MissedCallReport | None]
):
    """
    Check the signature of a post-call webhook of the voice platform and
    read a call it could not start (its caller did not get through); None
    for every other event.
    """

    def __init__(
        self,
        voice_webhook_adapter: VoiceWebhookAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._voice_webhook_adapter: VoiceWebhookAdapterContract = voice_webhook_adapter
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PostCallWebhookRequest) -> MissedCallReport | None:
        self._voice_webhook_adapter.verify_post_call_signature(
            input_data, self._wall_clock.now_unix()
        )
        return self._voice_webhook_adapter.parse_call_start_failure(input_data.body)
