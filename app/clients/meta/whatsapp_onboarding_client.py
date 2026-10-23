import httpx

from app.clients.meta.graph_api_client import GraphApiClient
from app.clients.meta.graph_requests import graph_request
from app.clients.meta.meta_app_proof import appsecret_proof
from app.clients.meta.meta_graph_errors import build_graph_error
from app.clients.meta.meta_graph_readers import read_object_id
from app.contracts.meta_connection import WhatsAppOnboardingClientContract
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.dto.channels.provider_profiles import WhatsAppPhoneNumberProfile
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.meta_connection_errors import WhatsAppPinMismatchError
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import WhatsAppDisplayPhoneNumber
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
    WhatsAppRegistrationPin,
)
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_integer,
    read_object,
    read_objects,
    read_text,
)

PHONE_NUMBER_FIELDS: str = "id,display_phone_number,verified_name"
# Graph error of a registration with a PIN other than the number's own.
PIN_MISMATCH_ERROR_CODE: int = 133005


class WhatsAppOnboardingClient(GraphApiClient, WhatsAppOnboardingClientContract):
    """
    The Cloud API steps after WhatsApp Embedded Signup, made with the
    business's own token (Authorization header, with the app's
    `appsecret_proof`):

    - `GET /{waba-id}/phone_numbers`: the numbers of its WhatsApp Business
      Account and the form customers see them in;
    - `POST /{waba-id}/subscribed_apps`: the platform's app gets the
      account's webhooks (messages, statuses);
    - `POST /{phone-number-id}/register`: the number starts working on the
      Cloud API with a two-step verification PIN (Meta's 133005, a number
      registered before with another PIN, raises WhatsAppPinMismatchError).
    """

    def list_phone_numbers(
        self,
        business_token: MetaAccessToken,
        account_id: WhatsAppBusinessAccountId,
        app: MetaAppCredentials,
    ) -> list[WhatsAppPhoneNumberProfile]:
        body: JsonObject = graph_request(
            self._http_client,
            "GET",
            f"/{account_id}/phone_numbers",
            str(business_token),
            params={
                "fields": PHONE_NUMBER_FIELDS,
                "appsecret_proof": appsecret_proof(str(business_token), app),
            },
            is_lookup=True,
        )
        numbers: list[WhatsAppPhoneNumberProfile] = []
        for number in read_objects(body, "data"):
            phone_number_id: MetaObjectId | None = read_object_id(number, "id")
            display: str | None = read_text(number, "display_phone_number")
            if phone_number_id is not None:
                numbers.append(
                    WhatsAppPhoneNumberProfile(
                        phone_number_id=phone_number_id,
                        display_phone_number=(
                            None
                            if display is None
                            else WhatsAppDisplayPhoneNumber(display)
                        ),
                    )
                )

        return numbers

    def subscribe_app(
        self,
        business_token: MetaAccessToken,
        account_id: WhatsAppBusinessAccountId,
        app: MetaAppCredentials,
    ) -> None:
        graph_request(
            self._http_client,
            "POST",
            f"/{account_id}/subscribed_apps",
            str(business_token),
            params={"appsecret_proof": appsecret_proof(str(business_token), app)},
            is_lookup=True,
        )

    def register_number(
        self,
        business_token: MetaAccessToken,
        phone_number_id: MetaObjectId,
        pin: WhatsAppRegistrationPin,
        app: MetaAppCredentials,
    ) -> None:
        try:
            response: httpx.Response = self._http_client.post(
                f"/{phone_number_id}/register",
                params={"appsecret_proof": appsecret_proof(str(business_token), app)},
                json={"messaging_product": "whatsapp", "pin": str(pin)},
                headers={"Authorization": f"Bearer {business_token}"},
            )
        except httpx.HTTPError as transport_error:
            raise ExternalServiceError(
                f"Meta Graph API request failed: {type(transport_error).__name__}."
            ) from None

        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code < 400 and "error" not in body:
            return

        error: JsonObject = read_object(body, "error") or {}
        if read_integer(error, "code") == PIN_MISMATCH_ERROR_CODE:
            raise WhatsAppPinMismatchError(
                "The WhatsApp number is registered with another two-step "
                "verification PIN."
            )

        raise build_graph_error(
            response.status_code,
            body,
            response.headers.get("Retry-After"),
            is_lookup=False,
        )
