import re

import httpx

from app.contracts.messaging_clients import TelegramGatewayClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_integers import OtpLifetimeSeconds
from app.schemas.typings.users.constrained_strings import OtpCode
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_text,
)

TELEGRAM_GATEWAY_BASE_URL: str = "https://gatewayapi.telegram.org"
REQUEST_TIMEOUT_SECONDS: float = 10.0
# Gateway errors are upper-case codes such as PHONE_NUMBER_INVALID; anything
# else is not echoed.
GATEWAY_ERROR_PATTERN: re.Pattern[str] = re.compile(r"^[A-Z0-9_]{1,64}$")


class TelegramGatewayClient(TelegramGatewayClientContract):
    """
    Telegram Gateway API (https://core.telegram.org/gateway/api): Telegram
    sends our code to the Telegram account of a phone number in its own
    verification chat. Charged only when the message is delivered.

    The API token travels in the Authorization header; errors carry the
    gateway's error code only.
    """

    def __init__(
        self,
        api_token: PlatformSecret,
        transport: httpx.BaseTransport | None = None,
        base_url: str = TELEGRAM_GATEWAY_BASE_URL,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
            headers={"Authorization": f"Bearer {api_token}"},
        )

    def send_verification_message(
        self,
        phone_number: E164PhoneNumber,
        code: OtpCode,
        lifetime_seconds: OtpLifetimeSeconds,
    ) -> None:
        try:
            response: httpx.Response = self._http_client.post(
                "/sendVerificationMessage",
                json={
                    "phone_number": str(phone_number),
                    "code": str(code),
                    "ttl": int(lifetime_seconds),
                },
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Telegram Gateway request failed: {type(error).__name__}."
            ) from None

        body: JsonObject | None = parse_json_object(response.content)
        if body is None:
            raise ExternalServiceError(
                f"Telegram Gateway returned HTTP {response.status_code} without "
                "a JSON body."
            )

        if body.get("ok") is True:
            return

        error_code: str = read_text(body, "error") or ""
        if GATEWAY_ERROR_PATTERN.fullmatch(error_code) is None:
            error_code = f"HTTP {response.status_code}"

        raise ExternalServiceError(f"Telegram Gateway refused the code: {error_code}.")
