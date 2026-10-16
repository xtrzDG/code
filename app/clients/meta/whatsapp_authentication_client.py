import httpx

from app.clients.meta.meta_graph_client import (
    DEFAULT_GRAPH_API_VERSION,
    META_GRAPH_BASE_URL,
)
from app.contracts.messaging_clients import WhatsAppAuthenticationClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import OtpCode
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_integer,
    read_object,
)

REQUEST_TIMEOUT_SECONDS: float = 10.0
# Graph error codes worth a sentence in the log; others are reported by code.
# 131026 (the number is not on WhatsApp) normally arrives later in the
# "failed" status webhook, not in this response: the API accepts the send,
# so the sign-in page offers another channel ("send by SMS instead").
KNOWN_ERRORS: dict[int, str] = {
    190: "the access token is invalid or expired",
    131026: "the number cannot receive WhatsApp messages",
    131030: "the number is not in the test number's allowed list",
    132000: "the template parameters do not match",
    132001: "the template does not exist in this language",
}


class WhatsAppAuthenticationClient(WhatsAppAuthenticationClientContract):
    """
    WhatsApp Cloud API authentication template: the platform number sends
    an approved "authentication" template whose body and copy-code button
    both carry the code.

    The token travels in the Authorization header; errors name the Graph
    error code, never the token or the code.
    """

    def __init__(
        self,
        access_token: PlatformSecret,
        phone_number_id: MetaObjectId,
        template_name: WhatsAppTemplateName,
        transport: httpx.BaseTransport | None = None,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        base_url: str = META_GRAPH_BASE_URL,
    ) -> None:
        self._messages_path: str = f"/{phone_number_id}/messages"
        self._template_name: WhatsAppTemplateName = template_name
        self._http_client: httpx.Client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/{api_version}",
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def send_authentication_code(
        self,
        recipient: E164PhoneNumber,
        code: OtpCode,
        language_code: WhatsAppTemplateLanguageCode,
    ) -> None:
        code_parameter: JsonObject = {"type": "text", "text": str(code)}
        payload: JsonObject = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": str(recipient).removeprefix("+"),
            "type": "template",
            "template": {
                "name": str(self._template_name),
                "language": {"code": str(language_code)},
                "components": [
                    {"type": "body", "parameters": [code_parameter]},
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [code_parameter],
                    },
                ],
            },
        }
        try:
            response: httpx.Response = self._http_client.post(
                self._messages_path,
                json=payload,
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"WhatsApp request failed: {type(error).__name__}."
            ) from None

        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code < 400 and "error" not in body:
            return

        graph_error: JsonObject = read_object(body, "error") or {}
        error_code: int | None = read_integer(graph_error, "code")
        if error_code is None:
            raise ExternalServiceError(
                f"WhatsApp refused the login code (HTTP {response.status_code})."
            )

        description: str = KNOWN_ERRORS.get(error_code, "see the Graph API docs")
        raise ExternalServiceError(
            f"WhatsApp refused the login code (error {error_code}): {description}."
        )
