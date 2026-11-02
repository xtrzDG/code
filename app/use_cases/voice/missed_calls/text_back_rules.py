"""
The rules of a text-back: in which language, through which channel, and
the callers who are not texted (opted out or blocked, already writing with
the business, texted in the last day, past the daily caps of unrequested
messages). Every contact holding the number counts for a refusal.
"""

from collections.abc import Sequence
from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.registries import CountryRegistryContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.schemas.constants.calls import TextBackChannel, TextBackSkipReason
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.calls.call_follow_up_keys import (
    business_text_back_key,
    caller_text_back_key,
)
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.proactive_limits import proactive_message_counter
from app.utilities.privacy.messaging_suppression import is_messaging_suppressed
from app.utilities.privacy.suppressed_identities import phone_identity

MICROSECONDS_PER_SECOND: int = 1_000_000
# A caller is texted within minutes; a report that arrives hours late (the
# worker was down) is not worth "you just called us".
TEXT_BACK_DEADLINE: timedelta = timedelta(hours=2)
# A caller who wrote to the business on a messenger lately is already in a
# conversation: staff and the assistant answer there.
ACTIVE_CONVERSATION_WINDOW: timedelta = timedelta(hours=24)
DAY_WINDOW: RateWindowSeconds = RateWindowSeconds(24 * 60 * 60)
CALLER_DAILY_LIMIT: RequestsPerWindow = RequestsPerWindow(1)
# Every text-back costs a WhatsApp template or an SMS; a flood of calls
# from many numbers is someone abusing the line.
BUSINESS_DAILY_LIMIT: RequestsPerWindow = RequestsPerWindow(200)


def text_back_deadline(called_at: Microseconds) -> Microseconds:
    """The last moment a text-back of this call is still worth sending."""

    return Microseconds(
        int(called_at)
        + int(TEXT_BACK_DEADLINE.total_seconds()) * MICROSECONDS_PER_SECOND
    )


def is_too_late(called_at: Microseconds, now: Microseconds) -> bool:
    return int(now) > int(text_back_deadline(called_at))


def choose_text_back_language(
    business: BusinessDocument,
    detected_language: LanguageTag | None,
    caller_phone_number: E164PhoneNumber | None,
    phone_number_parser: PhoneNumberParserContract,
    country_registry: CountryRegistryContract,
) -> LanguageTag:
    """
    The language the caller spoke on the call; else the first language of
    their phone's country when the business speaks it; else the
    business's default language.
    """

    if detected_language is not None:
        return detected_language

    if caller_phone_number is not None:
        try:
            country = phone_number_parser.parse(
                RawPhoneNumberInput(str(caller_phone_number)), None
            ).country_code
        except InvalidPhoneNumberError:
            return business.default_language

        for language in country_registry.get(country).default_customer_languages:
            if language in business.languages:
                return language

    return business.default_language


def choose_text_back_channel(
    settings: CallSettingsDocument,
    whatsapp_channel: ChannelDocument | None,
    is_sms_available: bool,
) -> TextBackChannel | None:
    """
    WhatsApp when the business's number is connected and the owner named
    the approved template; else SMS when it is on and configured.
    """

    if (
        settings.text_back_template_name is not None
        and whatsapp_channel is not None
        and is_channel_active(whatsapp_channel)
    ):
        return TextBackChannel.WHATSAPP

    if settings.is_sms_fallback_enabled and is_sms_available:
        return TextBackChannel.SMS

    return None


def is_in_conversation(
    conversation_repo: ConversationRepoContract,
    business: BusinessDocument,
    holders: Sequence[ContactDocument],
    now: Microseconds,
) -> bool:
    """
    A contact holding the number writes with the business in a messenger:
    a conversation staff own, or one with a message in the last day (calls
    do not count). It only holds a text-back back, so any holder counts.
    """

    window_start = Microseconds(
        int(now)
        - int(ACTIVE_CONVERSATION_WINDOW.total_seconds()) * MICROSECONDS_PER_SECOND
    )
    for contact in holders:
        open_ones = conversation_repo.list_by_contact(
            business.id, contact.id, status=ConversationStatus.HANDOFF
        )
        recent_ones = conversation_repo.list_by_contact(
            business.id, contact.id, last_message_from=window_start
        )
        if any(
            conversation.channel is not ChannelKind.PHONE
            and not conversation.is_sandbox
            and conversation.status is not ConversationStatus.CLOSED
            for conversation in [*open_ones, *recent_ones]
        ):
            return True

    return False


def is_caller_suppressed(
    suppression_list: SuppressionListContract,
    business_id: BusinessId,
    caller: E164PhoneNumber,
    holders: Sequence[ContactDocument],
) -> bool:
    """
    The number is not texted: it is on the suppression list, or a contact
    holding it said STOP or is blocked by staff (a refusal may follow a
    caller id; `contacts_holding_number`).
    """

    also = [phone_identity(caller)]
    return is_messaging_suppressed(suppression_list, business_id, None, also) or any(
        is_messaging_suppressed(suppression_list, business_id, holder, also)
        for holder in holders
    )


def text_back_counters(
    business: BusinessDocument,
    caller_phone_number: E164PhoneNumber,
    contact: ContactDocument | None,
) -> list[RateLimitCounter]:
    """
    One text-back per caller and day, a daily cap per business, and, for a
    known customer, their shared daily cap of unrequested messages.
    """

    counters: list[RateLimitCounter] = [
        RateLimitCounter(
            key=caller_text_back_key(business.id, caller_phone_number),
            limit=CALLER_DAILY_LIMIT,
        ),
        RateLimitCounter(
            key=business_text_back_key(business.id), limit=BUSINESS_DAILY_LIMIT
        ),
    ]
    if contact is not None:
        counters.append(proactive_message_counter(business.id, contact.id))

    return counters


def refusal_reason(
    business: BusinessDocument,
    caller_phone_number: E164PhoneNumber,
    refused_key: RateLimitKey,
) -> TextBackSkipReason:
    """
    Which daily limit refused the text-back: the caller was texted today,
    else a cap (the business's, or the customer's unrequested messages).
    """

    if refused_key == caller_text_back_key(business.id, caller_phone_number):
        return TextBackSkipReason.ALREADY_TEXTED

    return TextBackSkipReason.DAILY_LIMIT
