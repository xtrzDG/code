"""
The refund terms sentence of a deposit's line or reminder, in the
customer's language. A booking names the last moment a cancellation still
gets the deposit back (its start less the owner's refund cutoff, the
moment settling applies) or, once that has passed, says the deposit is not
refunded; a banquet request, whose event has no start time, names the
cutoff in hours before the event.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from babel.dates import format_timedelta
from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.deposits.constrained_integers import DepositRefundCutoffHours
from app.schemas.typings.deposits.strings import DepositRefundTermsText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.deposits.deposit_refund_terms_texts import (
    DEPOSIT_NOT_REFUNDABLE,
    DEPOSIT_REFUND_ANY_TIME_BEFORE_EVENT,
    DEPOSIT_REFUND_BEFORE_EVENT,
    DEPOSIT_REFUND_UNTIL,
)
from app.utilities.deposits.deposit_settlement import refund_deadline
from app.utilities.deposits.deposit_times import refund_deadline_text
from app.utilities.scheduling.localized_formatting import (
    choose_template_language,
    find_locale,
    isolate,
)

# Large enough that format_timedelta never rounds hours up to days.
HOURS_ONLY_THRESHOLD: int = 10_000


def refund_terms_text(
    resolver: LocalizedTextResolverContract,
    refund_cutoff: DepositRefundCutoffHours,
    starts_at: BookingStartsAtUnixSeconds | None,
    now: Microseconds,
    zone: ZoneInfo,
    language: LanguageTag,
) -> DepositRefundTermsText:
    """
    The terms of a booking (`starts_at`) or of a banquet request (None), in
    the language the deposit's line or reminder speaks.
    """

    deadline: Microseconds | None = (
        None if starts_at is None else refund_deadline(starts_at, refund_cutoff)
    )
    template: LocalizedText = terms_template(refund_cutoff, deadline, now)
    text_language: LanguageTag = choose_template_language(template, language)
    until: str = (
        ""
        if deadline is None
        else str(refund_deadline_text(deadline, now, zone, text_language))
    )
    hours: str = isolate(cutoff_hours_text(refund_cutoff, text_language), text_language)
    text: str = str(resolver.resolve(template, text_language))
    return DepositRefundTermsText(text.format(until=until, hours=hours))


def terms_template(
    refund_cutoff: DepositRefundCutoffHours,
    deadline: Microseconds | None,
    now: Microseconds,
) -> LocalizedText:
    if deadline is None:
        return (
            DEPOSIT_REFUND_BEFORE_EVENT
            if int(refund_cutoff) > 0
            else DEPOSIT_REFUND_ANY_TIME_BEFORE_EVENT
        )

    return DEPOSIT_REFUND_UNTIL if int(deadline) > int(now) else DEPOSIT_NOT_REFUNDABLE


def cutoff_hours_text(
    refund_cutoff: DepositRefundCutoffHours, language: LanguageTag
) -> str:
    """The cutoff in CLDR short hour units ("24 h", "24 ч", "24 Std.")."""

    return format_timedelta(
        timedelta(hours=int(refund_cutoff)),
        granularity="hour",
        threshold=HOURS_ONLY_THRESHOLD,
        format="short",
        locale=find_locale(language),
    )
