"""
The kinds of Telegram Bot API updates (core.telegram.org/bots/api#update),
to name what a business bot's webhook skipped (`skipped_webhook_parts`):
only new private messages from people are answered.
"""

from app.utilities.channels.json_values import JsonObject
from app.utilities.channels.skipped_webhook_parts import OTHER_KIND, known_kind

UPDATE_ID_FIELD: str = "update_id"
UPDATE_KINDS: frozenset[str] = frozenset(
    {
        "business_connection",
        "business_message",
        "callback_query",
        "channel_post",
        "chat_boost",
        "chat_join_request",
        "chat_member",
        "chosen_inline_result",
        "deleted_business_messages",
        "edited_business_message",
        "edited_channel_post",
        "edited_message",
        "inline_query",
        "message",
        "message_reaction",
        "message_reaction_count",
        "my_chat_member",
        "poll",
        "poll_answer",
        "pre_checkout_query",
        "purchased_paid_media",
        "removed_chat_boost",
        "shipping_query",
    }
)


def update_kind(update: JsonObject | None) -> str:
    """The update's kind: the one field besides `update_id`."""

    if update is None:
        return OTHER_KIND

    for field_name in update:
        if field_name != UPDATE_ID_FIELD:
            return known_kind(field_name, UPDATE_KINDS)

    return OTHER_KIND
