"""
Reading a WhatsApp Cloud API webhook beyond its customer messages: the
text of a message, and what the delivery carried that is not one
(statuses of the business's own messages, other subscribed fields,
reactions and system messages) for the log (`skipped_webhook_parts`).
"""

import logging

from app.utilities.channels.json_values import (
    JsonObject,
    read_integer,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.skipped_webhook_parts import known_kind

LOGGER: logging.Logger = logging.getLogger(__name__)

STATUS_KINDS: frozenset[str] = frozenset(
    {"sent", "delivered", "read", "failed", "deleted", "warning", "played"}
)
# Receipts of the platform's own replies arrive for every message sent.
ROUTINE_KINDS: frozenset[str] = frozenset(
    {"status:sent", "status:delivered", "status:read"}
)
# Webhook fields of the app subscription other than "messages".
CHANGE_FIELDS: frozenset[str] = frozenset(
    {
        "account_alerts",
        "account_review_update",
        "account_update",
        "business_capability_update",
        "calls",
        "flows",
        "group_lifecycle_update",
        "group_participant_update",
        "group_settings_update",
        "group_status_update",
        "history",
        "message_echoes",
        "message_template_quality_update",
        "message_template_status_update",
        "phone_number_name_update",
        "phone_number_quality_update",
        "security",
        "smb_app_state_sync",
        "smb_message_echoes",
        "template_category_update",
        "user_preferences",
    }
)
MESSAGE_TYPES: frozenset[str] = frozenset(
    {
        "audio",
        "button",
        "contacts",
        "document",
        "image",
        "interactive",
        "location",
        "order",
        "reaction",
        "request_welcome",
        "sticker",
        "system",
        "text",
        "unknown",
        "unsupported",
        "video",
    }
)
# Delivery failures worth naming (developers.facebook.com/docs/whatsapp/
# cloud-api/support/error-codes); any other code reads "other".
FAILURE_LABELS: dict[int, str] = {
    130472: "130472 user in a marketing experiment",
    131000: "131000 something went wrong",
    131021: "131021 recipient is the sender",
    131026: "131026 message undeliverable",
    131031: "131031 business account locked",
    131042: "131042 payment problem",
    131047: "131047 re-engagement window closed",
    131049: "131049 marketing message not delivered",
    131050: "131050 user stopped marketing messages",
    131051: "131051 unsupported message type",
    131053: "131053 media upload error",
    132000: "132000 template parameter count mismatch",
    132001: "132001 template does not exist",
}


def read_message_text(message: JsonObject) -> str | None:
    """
    Text of a customer message: typed text, a tapped template button or an
    interactive reply. Media and places are attachments
    (`whatsapp_attachments`); reactions have neither.
    """

    message_type: str | None = read_text(message, "type")
    if message_type == "text":
        return read_text(read_object(message, "text") or {}, "body")

    if message_type == "button":
        return read_text(read_object(message, "button") or {}, "text")

    if message_type == "interactive":
        interactive: JsonObject = read_object(message, "interactive") or {}
        for reply_key in ("button_reply", "list_reply"):
            reply: JsonObject | None = read_object(interactive, reply_key)
            if reply is not None:
                return read_text(reply, "title")

    return None


def other_field_kind(change: JsonObject) -> str:
    return "field:" + known_kind(read_text(change, "field"), CHANGE_FIELDS)


def skipped_message_kind(message: JsonObject) -> str:
    return "message:" + known_kind(read_text(message, "type"), MESSAGE_TYPES)


def status_kinds(value: JsonObject) -> list[str]:
    """
    One kind per status of the business's own messages; failures are
    logged as a warning with their error codes, since a reply or a
    notification did not reach its recipient.
    """

    kinds: list[str] = []
    failures: list[str] = []
    for status in read_objects(value, "statuses"):
        kind: str = known_kind(read_text(status, "status"), STATUS_KINDS)
        kinds.append("status:" + kind)
        if kind == "failed":
            failures.extend(failure_labels(status))

    if failures:
        LOGGER.warning(
            "WhatsApp could not deliver %d message(s): %s.",
            len(failures),
            ", ".join(sorted(failures)),
        )

    return kinds


def failure_labels(status: JsonObject) -> list[str]:
    errors: list[JsonObject] = read_objects(status, "errors")
    if not errors:
        return ["no error code"]

    return [
        FAILURE_LABELS.get(read_integer(error, "code") or 0, "other")
        for error in errors
    ]
