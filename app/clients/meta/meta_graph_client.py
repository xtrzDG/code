import httpx

from app.contracts.channel_clients import MetaGraphApiClientContract, ProviderToken
from app.schemas.dto.channels import MetaPageProfile, WhatsAppPhoneNumberProfile
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    MetaPageName,
    OutboundMessagePart,
    WhatsAppDisplayPhoneNumber,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_identifier,
    read_integer,
    read_object,
    read_text,
)

META_GRAPH_BASE_URL: str = "https://graph.facebook.com"
# Graph API version the payloads were written against; Meta keeps a version
# working for at least two years after the next one is released.
DEFAULT_GRAPH_API_VERSION: str = "v23.0"
REQUEST_TIMEOUT_SECONDS: float = 10.0
# Graph error codes meaning the caller's token or object id is wrong:
# 100 invalid parameter / unknown object, 190 invalid token, 200 permission,
# 803 unknown alias.
INVALID_INPUT_ERROR_CODES: frozenset[int] = frozenset({100, 190, 200, 803})
# After connecting, these mean the page or system user token stopped working
# (expired, revoked, permissions removed): 401 / 403, Graph code 102
# (session) and 190 (invalid OAuth token).
REJECTED_CREDENTIAL_STATUS_CODES: frozenset[int] = frozenset({401, 403})
REJECTED_CREDENTIAL_ERROR_CODES: frozenset[int] = frozenset({102, 190})
PAGE_WEBHOOK_FIELDS: str = "messages,messaging_postbacks"


class MetaGraphClient(MetaGraphApiClientContract):
    """
    Minimal Meta Graph API client for the WhatsApp Cloud API and the
    Messenger / Instagram Send API.

    Tokens travel in the Authorization header, never in URLs.
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        base_url: str = META_GRAPH_BASE_URL,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/{api_version}",
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def get_whatsapp_phone_number(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
    ) -> WhatsAppPhoneNumberProfile:
        body: JsonObject = self._request(
            "GET",
            f"/{phone_number_id}",
            access_token,
            params={"fields": "id,display_phone_number,verified_name"},
            is_lookup=True,
        )
        display_number: str | None = read_text(body, "display_phone_number")
        return WhatsAppPhoneNumberProfile(
            phone_number_id=read_object_id(body, "id") or phone_number_id,
            display_phone_number=(
                None
                if display_number is None
                else WhatsAppDisplayPhoneNumber(display_number)
            ),
        )

    def subscribe_whatsapp_business_account(
        self,
        access_token: ProviderToken,
        business_account_id: MetaObjectId,
    ) -> None:
        self._request(
            "POST",
            f"/{business_account_id}/subscribed_apps",
            access_token,
            is_lookup=True,
        )

    def get_page(
        self,
        access_token: ProviderToken,
        page_id: MetaObjectId,
    ) -> MetaPageProfile:
        body: JsonObject = self._request(
            "GET",
            f"/{page_id}",
            access_token,
            params={"fields": "id,name,instagram_business_account"},
            is_lookup=True,
        )
        page_name: str | None = read_text(body, "name")
        instagram_account: JsonObject | None = read_object(
            body,
            "instagram_business_account",
        )
        return MetaPageProfile(
            page_id=read_object_id(body, "id") or page_id,
            name=None if page_name is None else MetaPageName(page_name),
            instagram_account_id=(
                None
                if instagram_account is None
                else read_object_id(instagram_account, "id")
            ),
        )

    def subscribe_page(
        self,
        access_token: ProviderToken,
        page_id: MetaObjectId,
    ) -> None:
        self._request(
            "POST",
            f"/{page_id}/subscribed_apps",
            access_token,
            params={"subscribed_fields": PAGE_WEBHOOK_FIELDS},
            is_lookup=True,
        )

    def send_whatsapp_text(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        text: OutboundMessagePart,
    ) -> None:
        self._request(
            "POST",
            f"/{phone_number_id}/messages",
            access_token,
            json_body={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": str(recipient),
                "type": "text",
                "text": {"preview_url": False, "body": str(text)},
            },
        )

    def send_whatsapp_template(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[OutboundMessagePart],
    ) -> None:
        template: JsonObject = {
            "name": str(template_name),
            "language": {"code": str(language_code)},
        }
        if body_parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(parameter)}
                        for parameter in body_parameters
                    ],
                }
            ]

        self._request(
            "POST",
            f"/{phone_number_id}/messages",
            access_token,
            json_body={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": str(recipient),
                "type": "template",
                "template": template,
            },
        )

    def send_page_message(
        self,
        access_token: ProviderToken,
        recipient: ChannelUserId,
        text: OutboundMessagePart,
    ) -> None:
        self._request(
            "POST",
            "/me/messages",
            access_token,
            json_body={
                "recipient": {"id": str(recipient)},
                "messaging_type": "RESPONSE",
                "message": {"text": str(text)},
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        access_token: ProviderToken,
        params: dict[str, str] | None = None,
        json_body: JsonObject | None = None,
        is_lookup: bool = False,
    ) -> JsonObject:
        try:
            response: httpx.Response = self._http_client.request(
                method,
                path,
                params=params,
                json=json_body,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.HTTPError as transport_error:
            raise ExternalServiceError(
                f"Meta Graph API request failed: {type(transport_error).__name__}."
            ) from None

        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code < 400 and "error" not in body:
            return body

        error: JsonObject = read_object(body, "error") or {}
        error_code: int | None = read_integer(error, "code")
        message: str = read_text(error, "message") or f"HTTP {response.status_code}"
        if is_lookup and error_code in INVALID_INPUT_ERROR_CODES:
            raise ValidationFailedError(
                f"Meta did not accept the account or token: {message}"
            )

        if (
            response.status_code in REJECTED_CREDENTIAL_STATUS_CODES
            or error_code in REJECTED_CREDENTIAL_ERROR_CODES
        ):
            raise ChannelCredentialRejectedError(
                f"Meta rejected the access token or its permissions "
                f"({error_code or response.status_code}): {message}"
            )

        raise ExternalServiceError(
            f"Meta Graph API error {error_code or response.status_code}: {message}"
        )


def read_object_id(source: JsonObject, key: str) -> MetaObjectId | None:
    raw_id: str | None = read_identifier(source, key)
    if raw_id is None:
        return None

    try:
        return MetaObjectId(raw_id)
    except ValueError:
        return None
