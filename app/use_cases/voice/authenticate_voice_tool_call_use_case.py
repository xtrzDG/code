from app.contracts.channels import VoiceWebhookAdapterContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import VoiceToolCallRequest
from app.schemas.dto.voice_webhooks import (
    VoiceToolCallArguments,
    VoiceToolWebhookRequest,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.voice_service import (
    CALLER_ID_BOUND_TOOLS,
    CALLER_ID_REFUSAL,
)
from app.utilities.channels.voice_webhook_auth import require_voice_webhook_access


class AuthenticateVoiceToolCallUseCase(
    UseCaseContract[VoiceToolWebhookRequest, VoiceToolCallRequest]
):
    """
    Check a tool webhook of a business's voice agent and read the call.

    The request must carry the business's tool secret or an HMAC-SHA256
    signature of the raw body made with it (constant-time checks). The
    business comes from the verified credentials, never from the model's
    arguments; the caller id is read as a phone number of any country with
    the business country as the hint (withheld numbers stay unknown).

    The caller id is no proof of who calls, so the tools that read or
    change a customer's bookings by their identity (CALLER_ID_BOUND_TOOLS)
    are refused once the webhook is authenticated (AccessDeniedError with
    what the agent should do instead: hand the request to staff).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        voice_webhook_adapter: VoiceWebhookAdapterContract,
        phone_number_parser: PhoneNumberParserContract,
        app_settings: AppSettings,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._voice_webhook_adapter: VoiceWebhookAdapterContract = voice_webhook_adapter
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: VoiceToolWebhookRequest) -> VoiceToolCallRequest:
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

        if input_data.tool_name in CALLER_ID_BOUND_TOOLS:
            raise AccessDeniedError(CALLER_ID_REFUSAL)

        arguments: VoiceToolCallArguments = self._voice_webhook_adapter.parse_tool_call(
            input_data.body
        )
        return VoiceToolCallRequest(
            business_id=business.id,
            provider_call_id=arguments.provider_call_id,
            caller_phone_number=(
                None
                if arguments.caller_number is None
                else parse_messaging_phone_number(
                    self._phone_number_parser,
                    str(arguments.caller_number),
                    business.country_code,
                )
            ),
            tool_name=input_data.tool_name,
            input_json=arguments.input_json,
            language=arguments.language,
        )
