import re

import httpx

from app.contracts.login_protection import TurnstileVerificationClientContract
from app.schemas.dto.login_protection import TurnstileVerification
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import (
    TurnstileAction,
    TurnstileResponseToken,
)
from app.schemas.typings.users.strings import TurnstileErrorCode
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_strings,
    read_text,
)

TURNSTILE_API_BASE_URL: str = "https://challenges.cloudflare.com"
SITEVERIFY_PATH: str = "/turnstile/v0/siteverify"
REQUEST_TIMEOUT_SECONDS: float = 5.0
HTTP_OK: int = 200
# Siteverify error codes are lower-case words joined by dashes; anything
# else is not kept.
ERROR_CODE_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9\-]{1,64}$")
ACTION_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")


class TurnstileVerificationClient(TurnstileVerificationClientContract):
    """
    Cloudflare Turnstile server-side validation
    (https://developers.cloudflare.com/turnstile/get-started/server-side-validation/):
    the widget's token, the secret key and the visitor's address go to
    siteverify, which says whether the check was passed, for which action,
    and why not. A token is valid for 300 seconds and once.

    The secret key travels only in the form body; errors never repeat the
    token or the key.
    """

    def __init__(
        self,
        secret_key: PlatformSecret,
        transport: httpx.BaseTransport | None = None,
        base_url: str = TURNSTILE_API_BASE_URL,
    ) -> None:
        self._secret_key: PlatformSecret = secret_key
        self._http_client: httpx.Client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def verify(
        self,
        token: TurnstileResponseToken,
        client_ip_address: ClientIpAddress | None,
    ) -> TurnstileVerification:
        form: dict[str, str] = {
            "secret": str(self._secret_key),
            "response": str(token),
        }
        if client_ip_address is not None:
            form["remoteip"] = str(client_ip_address)

        try:
            response: httpx.Response = self._http_client.post(
                SITEVERIFY_PATH, data=form
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Turnstile siteverify request failed: {type(error).__name__}."
            ) from None

        body: JsonObject | None = parse_json_object(response.content)
        if response.status_code != HTTP_OK or body is None:
            raise ExternalServiceError(
                f"Turnstile siteverify returned HTTP {response.status_code}."
            )

        action: str | None = read_text(body, "action")
        return TurnstileVerification(
            is_passed=body.get("success") is True,
            action=(
                TurnstileAction(action)
                if action is not None and ACTION_PATTERN.fullmatch(action)
                else None
            ),
            error_codes=[
                TurnstileErrorCode(code)
                for code in read_strings(body, "error-codes")
                if ERROR_CODE_PATTERN.fullmatch(code)
            ],
        )
