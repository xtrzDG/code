"""
The kinds of Messenger and Instagram webhook events that carry no
customer message (developers.facebook.com/docs/messenger-platform/webhooks),
named for the log (`skipped_webhook_parts`).
"""

from app.utilities.channels.json_values import (
    JsonObject,
    read_flag,
    read_identifier,
    read_object,
    read_objects,
)
from app.utilities.channels.skipped_webhook_parts import OTHER_KIND, known_kind

ENVELOPE_FIELDS: frozenset[str] = frozenset({"sender", "recipient", "timestamp"})
EVENT_KINDS: frozenset[str] = frozenset(
    {
        "account_linking",
        "app_roles",
        "delivery",
        "game_play",
        "message_edit",
        "message_reactions",
        "messaging_feedback",
        "optin",
        "pass_thread_control",
        "policy_enforcement",
        "postback",
        "reaction",
        "read",
        "referral",
        "request_thread_control",
        "response_feedback",
        "take_thread_control",
    }
)
# Fields of an entry other than `messaging`: page and Instagram feed
# changes (comments, mentions) and messages of a thread another app owns.
ENTRY_FIELDS: tuple[str, ...] = ("changes", "standby")
# Receipts and echoes of the business's own messages arrive for every reply.
ROUTINE_KINDS: frozenset[str] = frozenset({"echo", "read", "delivery"})


def skipped_event_kind(event: JsonObject, account_id: str) -> str:
    """Why a `messaging` event gave no customer message."""

    sender: JsonObject = read_object(event, "sender") or {}
    message: JsonObject | None = read_object(event, "message")
    if (message is not None and read_flag(message, "is_echo")) or read_identifier(
        sender, "id"
    ) == account_id:
        return "echo"

    if message is not None:
        return "message:without content"

    for field_name in event:
        if field_name not in ENVELOPE_FIELDS:
            return known_kind(field_name, EVENT_KINDS)

    return OTHER_KIND


def other_entry_kinds(entry: JsonObject) -> list[str]:
    """One kind per item of an entry's fields other than `messaging`."""

    return [
        f"entry:{field_name}"
        for field_name in ENTRY_FIELDS
        for _ in read_objects(entry, field_name)
    ]
