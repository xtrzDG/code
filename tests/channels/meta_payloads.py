"""Meta webhook payloads (WhatsApp, Messenger, Instagram) and how to post them."""

from typing import Any

from app.utilities.channels.channel_endpoints import META_SIGNATURE_HEADER
from tests.channels.channels_payloads import HttpResponse, sign_meta, to_json_bytes
from tests.channels.testbed import ChannelsTestbed

PHONE_NUMBER_ID: str = "106540352242922"
PAGE_ID: str = "4410001"
INSTAGRAM_ID: str = "17841400000000001"


def whatsapp_message(
    sender: str,
    text: str = "Hola, ¿tienen mesa?",
    message_id: str = "wamid.1",
    message_type: str = "text",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "from": sender,
        "id": message_id,
        "timestamp": "1790856000",
        "type": message_type,
    }
    if message_type == "text":
        message["text"] = {"body": text}
    message.update(extra or {})
    return message


def whatsapp_webhook(
    messages: list[dict[str, Any]],
    phone_number_id: str = PHONE_NUMBER_ID,
    contacts: list[dict[str, Any]] | None = None,
    statuses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "metadata": {
            "display_phone_number": "+995 32 200 00 00",
            "phone_number_id": phone_number_id,
        },
        "contacts": contacts or [],
        "messages": messages,
    }
    if statuses is not None:
        value["statuses"] = statuses
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": value}]}],
    }


def page_webhook(
    object_name: str,
    account_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "object": object_name,
        "entry": [{"id": account_id, "time": 1790856000, "messaging": events}],
    }


def page_message(
    sender: str,
    text: str | None,
    account_id: str,
    mid: str = "mid.1",
    is_echo: bool = False,
) -> dict[str, Any]:
    message: dict[str, Any] = {"mid": mid}
    if text is not None:
        message["text"] = text
    if is_echo:
        message["is_echo"] = True
    return {
        "sender": {"id": sender},
        "recipient": {"id": account_id},
        "timestamp": 1790856000,
        "message": message,
    }


def post_meta(
    testbed: ChannelsTestbed,
    payload: dict[str, Any],
    signature: str | None = "valid",
) -> HttpResponse:
    body: bytes = to_json_bytes(payload)
    headers: dict[str, str] = {}
    if signature == "valid":
        headers[META_SIGNATURE_HEADER] = sign_meta(body)
    elif signature is not None:
        headers[META_SIGNATURE_HEADER] = signature
    return testbed.build_http_client().post(
        "/v1/channels/meta/webhook", content=body, headers=headers
    )
