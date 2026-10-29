from urllib.parse import quote

import httpx

from app.clients.elevenlabs.elevenlabs_errors import raise_for_error
from app.contracts.telephony_clients import ElevenLabsPhoneNumbersClientContract
from app.schemas.dto.phone_numbers.provisioning import VoicePlatformImport
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.strings import VoicePlatformPhoneNumberId
from app.utilities.channels.json_values import JsonObject, parse_json_object, read_text

API_KEY_HEADER: str = "xi-api-key"
REQUEST_TIMEOUT: httpx.Timeout = httpx.Timeout(20.0, connect=3.0)
NOT_FOUND_STATUS_CODE: int = 404
PHONE_NUMBERS_PATH: str = "/v1/convai/phone-numbers"


class ElevenLabsPhoneNumbersClient(ElevenLabsPhoneNumbersClientContract):
    """
    ElevenLabs Agents' phone numbers (header `xi-api-key`):

    - POST /v1/convai/phone-numbers imports a Twilio number (provider
      `twilio`, the account SID and auth token, so ElevenLabs points the
      number's voice webhook at itself and checks Twilio's signatures),
      assigned to an agent when one is given;
    - PATCH /v1/convai/phone-numbers/{id} assigns another agent (or none);
    - DELETE /v1/convai/phone-numbers/{id} removes it (404: already gone).

    The base URL selects the data residency, as for the agents.
    """

    def __init__(
        self,
        api_key: PlatformSecret,
        base_url: PublicBaseUrl,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=str(base_url).rstrip("/"),
            headers={API_KEY_HEADER: str(api_key)},
            timeout=REQUEST_TIMEOUT,
            transport=transport,
        )

    def import_twilio_number(
        self,
        request: VoicePlatformImport,
        account_sid: TwilioAccountSid,
        auth_token: PlatformSecret,
    ) -> VoicePlatformPhoneNumberId:
        payload: JsonObject = {
            "provider": "twilio",
            "phone_number": str(request.phone_number),
            "label": str(request.label),
            "sid": str(account_sid),
            "token": str(auth_token),
        }
        if request.agent_id is not None:
            payload["agent_id"] = str(request.agent_id)

        response: httpx.Response = self._perform("POST", PHONE_NUMBERS_PATH, payload)
        raise_for_error(response, PHONE_NUMBERS_PATH)
        number_id: str | None = read_text(
            parse_json_object(response.content) or {}, "phone_number_id"
        )
        if number_id is None:
            raise ExternalServiceError(
                "ElevenLabs imported a phone number without its id."
            )

        return VoicePlatformPhoneNumberId(number_id)

    def assign_agent(
        self,
        phone_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        path: str = number_path(phone_number_id)
        response: httpx.Response = self._perform(
            "PATCH",
            path,
            {"agent_id": None if agent_id is None else str(agent_id)},
        )
        raise_for_error(response, path)

    def delete_number(self, phone_number_id: VoicePlatformPhoneNumberId) -> None:
        path: str = number_path(phone_number_id)
        response: httpx.Response = self._perform("DELETE", path, None)
        if response.status_code != NOT_FOUND_STATUS_CODE:
            raise_for_error(response, path)

    def _perform(
        self, method: str, path: str, payload: JsonObject | None
    ) -> httpx.Response:
        try:
            return self._http_client.request(method, path, json=payload)
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"ElevenLabs phone numbers request failed: {type(error).__name__}."
            ) from None


def number_path(phone_number_id: VoicePlatformPhoneNumberId) -> str:
    """API path of an imported number; the id is one escaped path segment."""

    return f"{PHONE_NUMBERS_PATH}/{quote(str(phone_number_id), safe='')}"
