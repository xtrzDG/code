import httpx

from app.contracts.messaging_clients import SmsMessagingClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.constrained_strings import (
    SmsSenderId,
    TwilioAccountSid,
    TwilioMessagingServiceSid,
)
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_integer,
)

TWILIO_API_BASE_URL: str = "https://api.twilio.com"
REQUEST_TIMEOUT_SECONDS: float = 10.0


class TwilioMessagingClient(SmsMessagingClientContract):
    """
    Twilio Programmable Messaging: one SMS per call
    (POST /2010-04-01/Accounts/{AccountSid}/Messages.json).

    The sender is the Messaging Service when one is configured (Twilio then
    picks a number or an alphanumeric sender per country), else the "From"
    number. The auth token travels only in the Basic authorization header;
    errors name Twilio's numeric error code, never the token, the recipient
    or the text.
    """

    def __init__(
        self,
        account_sid: TwilioAccountSid,
        auth_token: PlatformSecret,
        sender: SmsSenderId | None,
        messaging_service_sid: TwilioMessagingServiceSid | None,
        transport: httpx.BaseTransport | None = None,
        base_url: str = TWILIO_API_BASE_URL,
    ) -> None:
        if sender is None and messaging_service_sid is None:
            raise ValueError("Twilio needs a sender number or a Messaging Service.")

        self._messages_path: str = f"/2010-04-01/Accounts/{account_sid}/Messages.json"
        self._sender: SmsSenderId | None = sender
        self._messaging_service_sid: TwilioMessagingServiceSid | None = (
            messaging_service_sid
        )
        self._http_client: httpx.Client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
            auth=httpx.BasicAuth(str(account_sid), str(auth_token)),
        )

    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        form: dict[str, str] = {"To": str(recipient), "Body": str(text)}
        if self._messaging_service_sid is not None:
            form["MessagingServiceSid"] = str(self._messaging_service_sid)
        elif self._sender is not None:
            form["From"] = str(self._sender)

        try:
            response: httpx.Response = self._http_client.post(
                self._messages_path,
                data=form,
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Twilio SMS request failed: {type(error).__name__}."
            ) from None

        if response.status_code < 400:
            return

        if response.status_code == 401:
            raise ExternalServiceError(
                "Twilio rejected the credentials; check TWILIO_ACCOUNT_SID and "
                "TWILIO_AUTH_TOKEN."
            )

        body: JsonObject = parse_json_object(response.content) or {}
        error_code: int | None = read_integer(body, "code")
        raise ExternalServiceError(
            f"Twilio refused the SMS (HTTP {response.status_code}"
            + ("" if error_code is None else f", error {error_code}")
            + ")."
        )
