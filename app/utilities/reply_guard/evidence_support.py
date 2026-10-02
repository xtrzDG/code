"""Whether a number of a reply is backed by the evidence, in any of its readings."""

from decimal import Decimal

from app.utilities.reply_guard.evidence_index import EvidenceIndex
from app.utilities.reply_guard.number_mention import (
    LocalTime,
    NumberMention,
    PartialDate,
)
from app.utilities.reply_guard.number_patterns import MIN_PHONE_DIGITS, NOON

# National and international forms of a phone share their last nine digits.
PHONE_SUFFIX_LENGTH: int = 9
NATIONAL_TRUNK_PREFIX: str = "0"


def is_supported(
    mention: NumberMention,
    trusted: EvidenceIndex,
    customer: EvidenceIndex | None = None,
) -> bool:
    """
    True when any reading is in the evidence. Prices and percentages must
    match a number of the trusted evidence; a plain number may also match a
    number the customer wrote or a part of an evidence date or time ("the
    5th" and "2026-10-05").
    """

    other: EvidenceIndex = customer if customer is not None else EvidenceIndex()
    supporting_amounts: frozenset[Decimal] = (
        trusted.amounts
        if mention.is_money or mention.is_percent
        else trusted.amounts
        | trusted.date_time_parts
        | other.amounts
        | other.date_time_parts
    )
    times: frozenset[LocalTime] = trusted.times | other.times
    if mention.amounts & supporting_amounts or mention.times & times:
        return True

    hour_hints: frozenset[int] = trusted.hour_hints | other.hour_hints
    if any(is_time_supported(time, hour_hints) for time in mention.times):
        return True

    dates: frozenset[PartialDate] = trusted.dates | other.dates
    if any(is_date_supported(date, dates) for date in mention.dates):
        return True

    digit_strings: frozenset[str] = trusted.digit_strings | other.digit_strings
    if mention.phone_digits is not None:
        return is_phone_supported(mention.phone_digits, digit_strings)

    return mention.is_plain_number and any(
        amount == amount.to_integral_value()
        and len(str(int(amount))) >= MIN_PHONE_DIGITS
        and is_phone_supported(str(int(amount)), digit_strings)
        for amount in mention.amounts
        if amount >= 0
    )


def is_time_supported(time: LocalTime, hour_hints: frozenset[int]) -> bool:
    """
    A full hour is supported by a bare hour the customer wrote as an hour
    ("at 7" supports "19:00" and "7 pm").
    """

    hour, minute = time
    if minute != 0:
        return False

    hour_readings: set[int] = {hour}
    if hour > NOON:
        hour_readings.add(hour - NOON)

    return bool(hour_readings & hour_hints)


def is_date_supported(date: PartialDate, dates: frozenset[PartialDate]) -> bool:
    year, month, day = date
    return any(
        evidence_month == month
        and evidence_day == day
        and (year is None or evidence_year is None or evidence_year == year)
        for evidence_year, evidence_month, evidence_day in dates
    )


def is_phone_supported(phone_digits: str, digit_strings: frozenset[str]) -> bool:
    """
    The same phone in the evidence, written in any form: with or without the
    country calling code or a national trunk "0" ("03-123-4567" and
    "+972 3-123-4567", "2222 3333" and "+965 2222 3333"). The shorter number
    must still have at least seven digits.
    """

    reply_forms: set[str] = {phone_digits, strip_trunk_prefix(phone_digits)}
    suffix: str = phone_digits[-PHONE_SUFFIX_LENGTH:]
    for evidence_digits in digit_strings:
        if phone_digits in evidence_digits or (
            len(phone_digits) >= PHONE_SUFFIX_LENGTH
            and evidence_digits.endswith(suffix)
        ):
            return True

        evidence_forms: set[str] = {
            evidence_digits,
            strip_trunk_prefix(evidence_digits),
        }
        for reply_form in reply_forms:
            for evidence_form in evidence_forms:
                shorter, longer = sorted((reply_form, evidence_form), key=len)
                if len(shorter) >= MIN_PHONE_DIGITS and longer.endswith(shorter):
                    return True

    return False


def strip_trunk_prefix(digits: str) -> str:
    """A national number without its trunk "0" ("0322123456" -> "322123456")."""

    return digits.removeprefix(NATIONAL_TRUNK_PREFIX)
