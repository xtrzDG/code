from app.contracts.channels import VoiceWebhookAdapterContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.voice_webhooks import (
    CallInitiationData,
    CallInitiationWebhookRequest,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.voice_webhook_auth import require_voice_webhook_access


class StartVoiceCallUseCase(
    UseCaseContract[CallInitiationWebhookRequest, CallInitiationData]
):
    """
    Answer the voice platform's call-initiation webhook: the first phrase of
    the call (concept section 7: who answers, that the call is recorded, how
    to reach a human) in the business's default language, built fresh for
    every call. Authenticated like the tool webhooks.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        voice_webhook_adapter: VoiceWebhookAdapterContract,
        phone_number_parser: PhoneNumberParserContract,
        build_call_greeting: UseCaseContract[CallGreetingRequest, CallGreeting],
        app_settings: AppSettings,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._voice_webhook_adapter: VoiceWebhookAdapterContract = voice_webhook_adapter
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._build_call_greeting: UseCaseContract[
            CallGreetingRequest, CallGreeting
        ] = build_call_greeting
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: CallInitiationWebhookRequest) -> CallInitiationData:
        require_voice_webhook_access(
            self._app_settings.elevenlabs_webhook_secret,
            input_data.credentials,
            input_data.body,
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.credentials.business_id
        )
        if business is None:
            raise NotFoundError("The business of this voice agent was not found.")

        caller_number: RawPhoneNumberInput | None = (
            self._voice_webhook_adapter.parse_call_initiation(input_data.body)
        )
        greeting: CallGreeting = self._build_call_greeting.run(
            CallGreetingRequest(business_id=business.id)
        )
        return CallInitiationData(
            business_id=business.id,
            first_message=greeting.text,
            language=greeting.language,
            caller_phone_number=(
                None
                if caller_number is None
                else parse_messaging_phone_number(
                    self._phone_number_parser,
                    str(caller_number),
                    business.country_code,
                )
            ),
        )
