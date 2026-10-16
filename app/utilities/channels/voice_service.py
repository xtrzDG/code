"""Whether the phone assistant may take a new call (concept section 7)."""

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.billing import PlanDefinition
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber

# The voice platform's tool that puts a caller through to staff, and the
# per-call variable telling the agent whether the business is open now.
TRANSFER_TOOL_NAME: str = "transfer_to_number"
OPEN_NOW_VARIABLE: str = "is_open_now"
OPEN_NOW_YES: str = "yes"
OPEN_NOW_NO: str = "no"
# Per-call variables of the "Current call" block: the business-local date
# and time, the next days, the time zone, a known caller's name and their
# next booking. The placeholders stand in until the call-initiation webhook
# answers (or when it cannot).
LOCAL_NOW_VARIABLE: str = "local_now"
NEXT_DAYS_VARIABLE: str = "next_days"
TIMEZONE_VARIABLE: str = "timezone"
CALLER_NAME_VARIABLE: str = "caller_name"
UPCOMING_BOOKING_VARIABLE: str = "upcoming_booking"
UNKNOWN_VALUE: str = "unknown"
NO_BOOKING_VALUE: str = "none"
CALL_VARIABLE_PLACEHOLDERS: dict[str, str] = {
    OPEN_NOW_VARIABLE: OPEN_NOW_NO,
    LOCAL_NOW_VARIABLE: UNKNOWN_VALUE,
    NEXT_DAYS_VARIABLE: UNKNOWN_VALUE,
    TIMEZONE_VARIABLE: UNKNOWN_VALUE,
    CALLER_NAME_VARIABLE: UNKNOWN_VALUE,
    UPCOMING_BOOKING_VARIABLE: NO_BOOKING_VALUE,
}
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
    (WhatsApp or SMS). None when nobody can take a call.
    """

    if profile is not None and profile.contacts.handoff_phone_number is not None:
        return profile.contacts.handoff_phone_number

    for contact in business.manager_contacts:
        if contact.channel in PHONE_CONTACT_CHANNELS:
            return E164PhoneNumber(str(contact.address))

    return None
