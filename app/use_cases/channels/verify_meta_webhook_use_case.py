from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.channels.channel_webhooks import MetaWebhookVerificationRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.channels.strings import MetaWebhookChallenge
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import is_matching_secret

SUBSCRIBE_MODE: str = "subscribe"


class VerifyMetaWebhookUseCase(
    UseCaseContract[MetaWebhookVerificationRequest, MetaWebhookChallenge]
):
    """
    Answer Meta's webhook verification (GET with hub.mode=subscribe,
    hub.verify_token and hub.challenge): echo the challenge when the token
    equals META_VERIFY_TOKEN, refuse otherwise.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: MetaWebhookVerificationRequest) -> MetaWebhookChallenge:
        verify_token: PlatformSecret | None = self._app_settings.meta_verify_token
        if (
            verify_token is None
            or input_data.mode != SUBSCRIBE_MODE
            or input_data.challenge is None
            or not is_matching_secret(str(verify_token), input_data.verify_token)
        ):
            raise AccessDeniedError("The Meta webhook verification was refused.")

        return input_data.challenge
