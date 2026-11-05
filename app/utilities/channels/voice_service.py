"""Whether the phone assistant may take a new call (concept section 7)."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.billing import PlanDefinition
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.channels.transfer_destinations import (
    is_transfer_destination_allowed,
)

# The voice platform's tool that puts a caller through to staff, and the
# per-call variables telling the agent whether the business is open now and
# where a transfer goes: the staff mobile only while the business is open
# and the owner allowed transfers, else NO_TRANSFER_VALUE (no transfer).
TRANSFER_TOOL_NAME: str = "transfer_to_number"
OPEN_NOW_VARIABLE: str = "is_open_now"
OPEN_NOW_YES: str = "yes"
OPEN_NOW_NO: str = "no"
TRANSFER_NUMBER_VARIABLE: str = "transfer_number"
NO_TRANSFER_VALUE: str = "none"
# Whether a transfer is possible on this call ("yes"/"no"): what the prompt
# sees, so the model never learns the staff number it could read out.
CAN_TRANSFER_VARIABLE: str = "can_transfer"
# Per-call variables of the "Current call" block: the business-local date
# and time, the next days and the time zone. The placeholders stand in
# until the call-initiation webhook answers (or when it cannot): closed,
# no transfer, unknown date. Nothing about the caller is among them: a
# caller id is no proof of who calls.
LOCAL_NOW_VARIABLE: str = "local_now"
NEXT_DAYS_VARIABLE: str = "next_days"
TIMEZONE_VARIABLE: str = "timezone"
UNKNOWN_VALUE: str = "unknown"
CALL_VARIABLE_PLACEHOLDERS: dict[str, str] = {
    OPEN_NOW_VARIABLE: OPEN_NOW_NO,
    CAN_TRANSFER_VARIABLE: OPEN_NOW_NO,
    TRANSFER_NUMBER_VARIABLE: NO_TRANSFER_VALUE,
    LOCAL_NOW_VARIABLE: UNKNOWN_VALUE,
    NEXT_DAYS_VARIABLE: UNKNOWN_VALUE,
    TIMEZONE_VARIABLE: UNKNOWN_VALUE,
}
# The tools that read or change a customer's bookings by who they are. On
# a call the only identity is the caller id, which anyone can fake, so the
# voice agent never runs them: staff call the number on the booking back.
CALLER_ID_BOUND_TOOLS: frozenset[AssistantToolName] = frozenset(
    {
        AssistantToolName.LIST_MY_BOOKINGS,
        AssistantToolName.CANCEL_BOOKING,
        AssistantToolName.RESCHEDULE_BOOKING,
    }
)
CALLER_ID_REFUSAL: str = (
    "On a phone call the caller's number does not prove who is calling, so "
    "bookings are not read out, cancelled or moved here. Do not say whether "
    "a booking exists. Offer to pass the request to a colleague with "
    "handoff_to_human: they call back the number on the booking. The "
    "customer can also use the link in their booking confirmation."
)
# Caps of one business's phone line against runaway costs and abuse: the
# calls the voice platform takes at once and in a day, and the minutes a
# day after which new calls go to the missed-call flow until midnight.
MAX_CONCURRENT_CALLS: int = 5
MAX_DAILY_CALLS: int = 300
MAX_DAILY_CALL_MINUTES: int = 600
# A free trial without a card on file (ABUSE-05: a trial nobody pays for
# is the cheapest way to run toll fraud through the platform).
MAX_TRIAL_DAILY_CALL_MINUTES: int = 60
PHONE_CONTACT_CHANNELS: frozenset[ManagerContactChannel] = frozenset(
    {ManagerContactChannel.WHATSAPP, ManagerContactChannel.SMS}
)


def find_voice_refusal(
    business: BusinessDocument,
    published_version: AssistantVersionDocument | None,
    plan: PlanDefinition,
    phone_channel: ChannelDocument | None,
) -> str | None:
    """
    Why a new call must not be answered, or None when it may: the business
    is live, its published version has voice, its plan includes voice and
    its phone number is connected. A paused business, a downgrade to a plan
    without voice, a version without voice or a disconnected number all
    switch the phone assistant off.
    """

    if business.status is not BusinessStatus.LIVE:
        return f"{business.name} is not live ({business.status.value})."

    if published_version is None or not published_version.is_voice_enabled:
        return f"The live assistant of {business.name} has no voice."

    if not plan.is_voice_included:
        return f"The plan of {business.name} does not include voice."

    if phone_channel is None or phone_channel.status is not ChannelStatus.CONNECTED:
        return f"{business.name} has no connected phone number."

    return None


def find_transfer_phone_number(
    business: BusinessDocument,
    profile: BusinessProfileDocument | None,
) -> E164PhoneNumber | None:
    """
    The staff mobile a caller is put through to in opening hours: the
    profile's handoff phone, else the first manager reachable by phone
    (WhatsApp or SMS), whichever is an allowed transfer destination
    (`transfer_destinations`: a mobile or landline of the business's
    country or the EU, never a premium range). None when nobody can take
    a call.
    """

    candidates: list[E164PhoneNumber] = []
    if profile is not None and profile.contacts.handoff_phone_number is not None:
        candidates.append(profile.contacts.handoff_phone_number)

    candidates.extend(
        E164PhoneNumber(str(contact.address))
        for contact in business.manager_contacts
        if contact.channel in PHONE_CONTACT_CHANNELS
    )
    for candidate in candidates:
        if is_transfer_destination_allowed(candidate, business.country_code):
            return candidate

    return None
