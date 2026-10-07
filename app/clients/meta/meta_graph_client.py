import httpx

from app.clients.meta.graph_requests import graph_request
from app.clients.meta.meta_graph_readers import (
    read_instagram_username,
    read_object_id,
    read_page_username,
    read_whatsapp_message_id,
)
from app.contracts.channel_clients import MetaGraphApiClientContract, ProviderToken
from app.schemas.dto.channels.provider_profiles import (
    MetaPageProfile,
    WhatsAppPhoneNumberProfile,
)
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
from app.utilities.channels.json_values import (
    JsonObject,
    read_identifier,
    read_object,
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

    def send_whatsapp_interactive(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        interactive: JsonObject,
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
                    "type": "interactive",
                    "interactive": interactive,
                },
            )
        )

    def send_page_message(
        self,
        access_token: ProviderToken,
        recipient: ChannelUserId,
        text: OutboundMessagePart,
        quick_replies: list[JsonObject] | None = None,
    ) -> ProviderMessageId | None:
        message: JsonObject = {"text": str(text)}
        if quick_replies:
            message["quick_replies"] = list(quick_replies)

        sent: JsonObject = self._request(
            "POST",
            "/me/messages",
            access_token,
            json_body={
                "recipient": {"id": str(recipient)},
                "messaging_type": "RESPONSE",
                "message": message,
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
        return graph_request(
            self._http_client,
            method,
            path,
            str(access_token),
            params=params,
            json_body=json_body,
            is_lookup=is_lookup,
        )
