from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import VoiceWebhookAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.voice_webhooks import FinishedCallReport, PostCallWebhookRequest
from app.use_cases.voice.finished_call.call_staff_part import without_staff_part


class AuthenticatePostCallUseCase(
    UseCaseContract[PostCallWebhookRequest, FinishedCallReport | None]
):
    """
    Check the signature of a post-call webhook (HMAC with the platform's
    webhook secret, at most 30 minutes old) and read the finished call.
    Events that are not a finished call transcript read as None. A call a
    person took after a transfer is read without its staff part
    (`without_staff_part`), so no later step stores or analyses it.
    """

    def __init__(
        self,
        voice_webhook_adapter: VoiceWebhookAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._voice_webhook_adapter: VoiceWebhookAdapterContract = voice_webhook_adapter
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PostCallWebhookRequest) -> FinishedCallReport | None:
        self._voice_webhook_adapter.verify_post_call_signature(
            input_data,
            self._wall_clock.now_unix(),
        )
        report: FinishedCallReport | None = self._voice_webhook_adapter.parse_post_call(
            input_data.body
        )
        return None if report is None else without_staff_part(report)
