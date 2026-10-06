"""The join_waitlist result as the language model reads it."""

from app.schemas.dto.growth.waitlist_joining import WaitlistJoinReceipt
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.utilities.conversations.tool_payloads import render, with_business_today

JOINED_NOTE: str = (
    "The customer is on the waitlist. Tell them that if a place frees up the "
    "business writes to them here and holds it for hold_minutes minutes, "
    "and that nothing is booked yet; promise no place."
)
ALREADY_WAITING_NOTE: str = (
    "The customer was already waiting for this day; their wish was updated. "
    "Tell them nothing is booked yet."
)
WEB_CHAT_ONLY_NOTE: str = (
    "This customer can be reached only in this website chat: tell them to "
    "keep the chat open or to leave a phone number with a messenger so an "
    "offer reaches them."
)


def render_waitlist_join(
    receipt: WaitlistJoinReceipt,
    business_today: str | None = None,
) -> LlmToolResultJson:
    """The stored wish, the hold time and what to tell the customer."""

    payload: dict[str, object] = {
        "entry_id": str(receipt.entry_id),
        "date": str(receipt.date),
        "party_size": int(receipt.party_size),
        "hold_minutes": int(receipt.hold_minutes),
        "timezone": str(receipt.timezone),
        "note": ALREADY_WAITING_NOTE if receipt.is_already_waiting else JOINED_NOTE,
    }
    if receipt.time_from is not None:
        payload["time_from"] = str(receipt.time_from)

    if receipt.time_to is not None:
        payload["time_to"] = str(receipt.time_to)

    if receipt.nights is not None:
        payload["nights"] = int(receipt.nights)

    if receipt.service_title is not None:
        payload["service"] = str(receipt.service_title)

    if receipt.resource_name is not None:
        payload["resource_name"] = str(receipt.resource_name)

    if receipt.is_web_chat_only:
        payload["reach"] = WEB_CHAT_ONLY_NOTE

    return render(with_business_today(payload, business_today))
