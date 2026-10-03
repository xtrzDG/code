import httpx

from app.clients.meta.meta_graph_errors import build_graph_error
from app.contracts.channel_clients import MetaGraphApiClientContract, ProviderToken
from app.schemas.dto.channels.provider_profiles import (
    MetaPageProfile,
    WhatsAppPhoneNumberProfile,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    MetaPageName,
    OutboundMessagePart,
    ProviderMessageId,
    WhatsAppDisplayPhoneNumber,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    MetaPageUsername,
)
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_identifier,
    read_object,
    read_objects,
    read_text,
)

META_GRAPH_BASE_URL: str = "https://graph.facebook.com"
# Graph API version the payloads were written against; Meta keeps a version
# working for at least two years after the next one is released.
DEFAULT_GRAPH_API_VERSION: str = "v23.0"
REQUEST_TIMEOUT_SECONDS: float = 10.0
PAGE_WEBHOOK_FIELDS: str = "messages,messaging_postbacks"
# The page and its Instagram account with the public usernames chat links
# (m.me, ig.me) open.
PAGE_PROFILE_FIELDS: str = "id,name,username,instagram_business_account{id,username}"


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
            params={"fields": PAGE_PROFILE_FIELDS},
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
            username=read_page_username(body),
            instagram_account_id=(
                None
                if instagram_account is None
                else read_object_id(instagram_account, "id")
            ),
            instagram_username=(
                None
                if instagram_account is None
                else read_instagram_username(instagram_account)
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
    ) -> ProviderMessageId | None:
        return read_whatsapp_message_id(
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
        )

    def send_whatsapp_template(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[OutboundMessagePart],
    ) -> ProviderMessageId | None:
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

        return read_whatsapp_message_id(
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
        )

    def send_page_message(
        self,
        access_token: ProviderToken,
        recipient: ChannelUserId,
        text: OutboundMessagePart,
    ) -> ProviderMessageId | None:
        sent: JsonObject = self._request(
            "POST",
            "/me/messages",
            access_token,
            json_body={
                "recipient": {"id": str(recipient)},
                "messaging_type": "RESPONSE",
                "message": {"text": str(text)},
            },
        )
        message_id: str | None = read_identifier(sent, "message_id")
        return None if message_id is None else ProviderMessageId(message_id)

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

        raise build_graph_error(
            response.status_code,
            body,
            response.headers.get("Retry-After"),
            is_lookup=is_lookup,
        )


def read_object_id(source: JsonObject, key: str) -> MetaObjectId | None:
    raw_id: str | None = read_identifier(source, key)
    if raw_id is None:
        return None

    try:
        return MetaObjectId(raw_id)
    except ValueError:
        return None


def read_page_username(source: JsonObject) -> MetaPageUsername | None:
    raw_username: str | None = read_text(source, "username")
    try:
        return None if raw_username is None else MetaPageUsername(raw_username)
    except ValueError:
        return None


def read_instagram_username(source: JsonObject) -> InstagramUsername | None:
    raw_username: str | None = read_text(source, "username")
    try:
        return None if raw_username is None else InstagramUsername(raw_username)
    except ValueError:
        return None


def read_whatsapp_message_id(body: JsonObject) -> ProviderMessageId | None:
    """The "wamid..." of a sent WhatsApp message (`messages[0].id`)."""

    messages: list[JsonObject] = read_objects(body, "messages")
    message_id: str | None = read_identifier(messages[0], "id") if messages else None
    return None if message_id is None else ProviderMessageId(message_id)
