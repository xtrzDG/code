from app.contracts.channels import VoiceWebhookAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.voice_webhooks import FinishedCallReport, PostCallWebhookRequest


class ReadAcceptedPostCallUseCase(
    UseCaseContract[PostCallWebhookRequest, FinishedCallReport | None]
):
    """
    Read a finished-call report from the inbox: its signature was checked
    when the webhook stored it, so it is only parsed here (the post-call
    flow's authentication step when the worker processes the report).
    """

    def __init__(self, voice_webhook_adapter: VoiceWebhookAdapterContract) -> None:
        self._voice_webhook_adapter: VoiceWebhookAdapterContract = voice_webhook_adapter

    def run(self, input_data: PostCallWebhookRequest) -> FinishedCallReport | None:
        return self._voice_webhook_adapter.parse_post_call(input_data.body)
