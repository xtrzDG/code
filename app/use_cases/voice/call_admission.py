"""
Whether a new call is taken, and where it may be put through (concept
section 7).

A caller id is not proof of who calls: anyone can present someone else's
number. So the agent learns nothing about the caller from it (no name, no
bookings), and the number only ever counts against the caller: a number
a staff member blocked is refused, so a blocked customer cannot reach the
voice agent by phone either. The business's daily call minutes are
capped (`MAX_DAILY_CALL_MINUTES`), and a call is put through to staff only
while the business is open, the owner confirmed the staff notice of
transfers (Settings → Calls) and the staff number is an allowed
destination (`find_transfer_phone_number`).
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.spend_guard_repositories import (
    UsageSpendRepoContract,
)
from app.schemas.constants.billing import UsageKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.spend_guard import UsageKindTotal
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.channels.voice_service import (
    MAX_DAILY_CALL_MINUTES,
    find_transfer_phone_number,
)
from app.utilities.scheduling.zoned_time import (
    MICROSECONDS_PER_SECOND,
    SECONDS_PER_MINUTE,
    load_time_zone,
    local_day_start_microseconds,
    to_local_moment,
)

ONE_DAY: timedelta = timedelta(days=1)
BLOCKED_CALLER_REFUSAL: str = (
    "The caller's number is blocked by the business: the voice assistant does "
    "not take the call."
)
DAILY_MINUTES_REFUSAL: str = (
    f"The business used its {MAX_DAILY_CALL_MINUTES} call minutes of today: the "
    "voice assistant takes no calls until its midnight."
)


def refuse_blocked_caller(
    contact_repo: ContactRepoContract,
    business: BusinessDocument,
    caller_phone_number: E164PhoneNumber | None,
) -> None:
    """
    Refuse a call from a number staff blocked: a contact of the business
    with that phone (proved by a channel or given) and a block.

    Raises:
        ConflictError: the number is blocked.
    """

    if caller_phone_number is None:
        return

    contacts: list[ContactDocument | None] = [
        contact_repo.find_by_verified_phone_number(business.id, caller_phone_number),
        contact_repo.find_by_phone_number(business.id, caller_phone_number),
    ]
    if any(contact is not None and contact.block is not None for contact in contacts):
        raise ConflictError(BLOCKED_CALLER_REFUSAL)


def refuse_past_daily_minutes(
    usage_spend_repo: UsageSpendRepoContract,
    business: BusinessDocument,
    now: Microseconds,
) -> None:
    """
    Refuse a call once the business's calls of its local day lasted
    MAX_DAILY_CALL_MINUTES (summed by the database from the calls' usage).

    Raises:
        ConflictError: the day's call minutes are used up.
    """

    zone = load_time_zone(business.timezone)
    local_date = to_local_moment(int(now) // MICROSECONDS_PER_SECOND, zone).date()
    totals: list[UsageKindTotal] = usage_spend_repo.sum_business(
        business.id,
        Microseconds(local_day_start_microseconds(local_date, zone)),
        Microseconds(local_day_start_microseconds(local_date + ONE_DAY, zone)),
    )
    voice_seconds: int = sum(
        int(total.quantity) for total in totals if total.kind is UsageKind.VOICE_SECONDS
    )
    if voice_seconds >= MAX_DAILY_CALL_MINUTES * SECONDS_PER_MINUTE:
        raise ConflictError(DAILY_MINUTES_REFUSAL)


def find_call_transfer_number(
    business: BusinessDocument,
    profile: BusinessProfileDocument | None,
    call_settings: CallSettingsDocument | None,
    is_open_now: bool,
) -> E164PhoneNumber | None:
    """
    The staff number this call may be put through to: only while the
    business is open and once the owner confirmed the staff notice of
    transfers; None means the agent hands off instead (a colleague calls
    back).
    """

    if not is_open_now:
        return None

    if call_settings is None or not call_settings.is_staff_transfer_confirmed:
        return None

    return find_transfer_phone_number(business, profile)
