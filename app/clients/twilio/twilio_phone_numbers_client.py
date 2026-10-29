from urllib.parse import quote

import httpx

from app.clients.twilio.twilio_number_readers import (
    AVAILABLE_NUMBERS_RESOURCE,
    UNAVAILABLE_NUMBER_CODES,
    read_available_numbers,
    read_monthly_price,
)
from app.contracts.telephony_clients import TwilioPhoneNumbersClientContract
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.phone_numbers.provisioning import (
    AvailablePhoneNumber,
    PhoneNumberPurchase,
    PhoneNumberSearchQuery,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.phone_number_errors import PhoneNumberUnavailableError
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import VoiceFallbackUrl
from app.schemas.typings.telephony.strings import ProviderPhoneNumberId
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_integer,
    read_text,
)

TWILIO_API_BASE_URL: str = "https://api.twilio.com"
TWILIO_PRICING_BASE_URL: str = "https://pricing.twilio.com"
REQUEST_TIMEOUT: httpx.Timeout = httpx.Timeout(15.0, connect=3.0)
NOT_FOUND_STATUS_CODE: int = 404


class TwilioPhoneNumbersClient(TwilioPhoneNumbersClientContract):
    """
    Twilio's phone numbers, with the account's SID and auth token (Basic
    authorization; the token never leaves the header):

    - GET /2010-04-01/Accounts/{sid}/AvailablePhoneNumbers/{country}/
      {Local|Mobile|TollFree}.json with VoiceEnabled and the three
      Exclude*AddressRequired filters (InLocality narrows to a city);
    - GET https://pricing.twilio.com/v1/PhoneNumbers/Countries/{country},
      the monthly price of each kind;
    - POST /2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json to rent one
      (PhoneNumber, FriendlyName);
    - POST /2010-04-01/Accounts/{sid}/IncomingPhoneNumbers/{PN sid}.json
      with VoiceFallbackUrl and VoiceFallbackMethod, the call fallback;
    - DELETE /2010-04-01/Accounts/{sid}/IncomingPhoneNumbers/{PN sid}.json
      to return it.

    A country or kind Twilio does not sell answers 404: no numbers, no
    price. Errors name Twilio's numeric code, never the number or the token.
    """

    def __init__(
        self,
        account_sid: TwilioAccountSid,
        auth_token: PlatformSecret,
        transport: httpx.BaseTransport | None = None,
        base_url: str = TWILIO_API_BASE_URL,
        pricing_base_url: str = TWILIO_PRICING_BASE_URL,
    ) -> None:
        self._account_path: str = f"/2010-04-01/Accounts/{account_sid}"
        self._pricing_base_url: str = pricing_base_url.rstrip("/")
        self._http_client: httpx.Client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=REQUEST_TIMEOUT,
            transport=transport,
            auth=httpx.BasicAuth(str(account_sid), str(auth_token)),
        )

    def list_available_numbers(
        self, query: PhoneNumberSearchQuery
    ) -> list[AvailablePhoneNumber]:
        params: dict[str, str] = {
            "VoiceEnabled": "true",
            "ExcludeAllAddressRequired": "true",
            "ExcludeLocalAddressRequired": "true",
            "ExcludeForeignAddressRequired": "true",
            "Beta": "false",
            "PageSize": str(int(query.limit)),
        }
        if query.city is not None:
            params["InLocality"] = str(query.city)

        path: str = (
            f"{self._account_path}/AvailablePhoneNumbers/"
            f"{quote(str(query.country_code), safe='')}/"
            f"{AVAILABLE_NUMBERS_RESOURCE[query.number_type]}.json"
        )
        body: JsonObject | None = self._read("GET", path, params=params)
        return [] if body is None else read_available_numbers(body)

    def get_monthly_price(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> CostMicroUsd | None:
        body: JsonObject | None = self._read(
            "GET",
            f"{self._pricing_base_url}/v1/PhoneNumbers/Countries/"
            f"{quote(str(country_code), safe='')}",
        )
        return None if body is None else read_monthly_price(body, number_type)

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProviderPhoneNumberId:
        response: httpx.Response = self._perform(
            "POST",
            f"{self._account_path}/IncomingPhoneNumbers.json",
            data={
                "PhoneNumber": str(purchase.phone_number),
                "FriendlyName": str(purchase.label),
            },
        )
        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code >= 400:
            if read_integer(body, "code") in UNAVAILABLE_NUMBER_CODES:
                raise PhoneNumberUnavailableError(
                    "This number is no longer available. Search again and "
                    "pick another one."
                )

            raise describe_failure(response.status_code, body)

        sid: str | None = read_text(body, "sid")
        if sid is None:
            raise ExternalServiceError("Twilio rented a number without its SID.")

        return ProviderPhoneNumberId(sid)

    def set_voice_fallback(
        self, provider_number_id: ProviderPhoneNumberId, url: VoiceFallbackUrl
    ) -> None:
        response: httpx.Response = self._perform(
            "POST",
            self._number_path(provider_number_id),
            data={"VoiceFallbackUrl": str(url), "VoiceFallbackMethod": "POST"},
        )
        if response.status_code >= 400:
            raise describe_failure(
                response.status_code, parse_json_object(response.content) or {}
            )

    def release_number(self, provider_number_id: ProviderPhoneNumberId) -> None:
        response: httpx.Response = self._perform(
            "DELETE", self._number_path(provider_number_id)
        )
        if response.status_code >= 400 and response.status_code != (
            NOT_FOUND_STATUS_CODE
        ):
            raise describe_failure(
                response.status_code, parse_json_object(response.content) or {}
            )

    def _number_path(self, provider_number_id: ProviderPhoneNumberId) -> str:
        return (
            f"{self._account_path}/IncomingPhoneNumbers/"
            f"{quote(str(provider_number_id), safe='')}.json"
        )

    def _read(
        self, method: str, url: str, params: dict[str, str] | None = None
    ) -> JsonObject | None:
        """The answer's body; None for 404 (nothing of the kind there)."""

        response: httpx.Response = self._perform(method, url, params=params)
        if response.status_code == NOT_FOUND_STATUS_CODE:
            return None

        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code >= 400:
            raise describe_failure(response.status_code, body)

        return body

    def _perform(
        self,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            return self._http_client.request(method, url, params=params, data=data)
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Twilio phone numbers request failed: {type(error).__name__}."
            ) from None


def describe_failure(status_code: int, body: JsonObject) -> ExternalServiceError:
    """Twilio's refusal with its HTTP status and numeric code, nothing else."""

    if status_code == 401:
        return ExternalServiceError(
            "Twilio rejected the credentials; check TWILIO_ACCOUNT_SID and "
            "TWILIO_AUTH_TOKEN."
        )

    code: int | None = read_integer(body, "code")
    return ExternalServiceError(
        f"Twilio phone numbers request returned HTTP {status_code}"
        + ("" if code is None else f", error {code}")
        + "."
    )
