"""Validation of the structured profile sections (concept section 3).

Shared by saving one wizard step and saving the whole profile, so both
paths store the same data. Owner texts are checked (not blank, not too long)
and stored as written; phones become E.164.
"""

from collections.abc import Sequence

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessLink,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.profiles import BookingRulesInput, ContactsInput
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_integers import SlotDurationMinutes
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.profiles.strings import ToneText

MAX_ADDRESS_LENGTH: int = 500
MAX_RULES: int = 30
MAX_RULE_LENGTH: int = 300
MAX_TONE_LENGTH: int = 200
MAX_CANCELLATION_POLICY_LENGTH: int = 1000
NIGHT_SLOT_MINUTES: SlotDurationMinutes = SlotDurationMinutes(24 * 60)
DEFAULT_SLOT_MINUTES: SlotDurationMinutes = SlotDurationMinutes(60)


def check_address(address: BusinessAddress | None) -> BusinessAddress | None:
    """The address as written; a blank or overly long text is rejected."""

    if address is None:
        return None

    check_text_length(address.text, MAX_ADDRESS_LENGTH, "The address")
    return address.model_copy()


def parse_contacts(
    contacts_input: ContactsInput,
    phone_number_parser: PhoneNumberParserContract,
    business: BusinessDocument,
) -> BusinessContacts:
    """
    Phones of any country in E.164.

    National formats are read with the business country as a hint, so
    "555 12 34 56" works in Georgia and "030 1234567" in Germany.
    """

    return BusinessContacts(
        public_phone_number=parse_optional_phone(
            contacts_input.public_phone_number,
            phone_number_parser,
            business,
        ),
        handoff_phone_number=parse_optional_phone(
            contacts_input.handoff_phone_number,
            phone_number_parser,
            business,
        ),
    )


def parse_optional_phone(
    raw_phone_number: RawPhoneNumberInput | None,
    phone_number_parser: PhoneNumberParserContract,
    business: BusinessDocument,
) -> E164PhoneNumber | None:
    if raw_phone_number is None or raw_phone_number.strip() == "":
        return None

    return phone_number_parser.parse(
        raw_phone_number,
        country_hint=business.country_code,
    ).e164


def build_booking_rules(
    rules_input: BookingRulesInput | None,
    template: NicheTemplate,
    business: BusinessDocument,
) -> BookingRules | None:
    """
    Booking rules with niche defaults and the deposit in the business currency.

    Raises:
        ValidationFailedError: the niche takes no bookings, or the deposit is
            in another currency.
    """

    if rules_input is None:
        return None

    if not template.takes_bookings:
        raise ValidationFailedError(
            f"Niche {template.key} takes no bookings; leave the booking rules empty."
        )

    if (
        rules_input.deposit_currency_code is not None
        and rules_input.deposit_currency_code != business.currency_code
    ):
        raise ValidationFailedError(
            f"The deposit must be in the business currency {business.currency_code}, "
            f"not {rules_input.deposit_currency_code}."
        )

    resource_kind: ResourceKind = (
        rules_input.resource_kind
        if rules_input.resource_kind is not None
        else template.resource_kind
    )
    slot_minutes: SlotDurationMinutes = rules_input.slot_minutes or (
        NIGHT_SLOT_MINUTES
        if template.booking_unit is BookingUnit.NIGHT
        else DEFAULT_SLOT_MINUTES
    )
    has_deposit: bool = rules_input.deposit_minor is not None and (
        rules_input.deposit_minor > 0
    )
    return BookingRules(
        resource_kind=resource_kind,
        slot_minutes=slot_minutes,
        max_party_size=rules_input.max_party_size,
        min_notice_minutes=rules_input.min_notice_minutes,
        deposit_minor=rules_input.deposit_minor if has_deposit else None,
        deposit_currency_code=business.currency_code if has_deposit else None,
        cancellation_policy=check_optional_text(
            rules_input.cancellation_policy,
            MAX_CANCELLATION_POLICY_LENGTH,
            "The cancellation policy",
        ),
    )


def check_rules[RuleText: str](
    rules: Sequence[RuleText],
    subject: str,
) -> list[RuleText]:
    """
    Rules as written, without blank entries and repeats (ignoring case and
    surrounding spaces).
    """

    kept: list[RuleText] = []
    seen: set[str] = set()
    for rule in rules:
        folded: str = rule.strip().casefold()
        if folded == "" or folded in seen:
            continue

        check_text_length(rule, MAX_RULE_LENGTH, f"Each {subject} rule")
        seen.add(folded)
        kept.append(rule)

    if len(kept) > MAX_RULES:
        raise ValidationFailedError(f"At most {MAX_RULES} {subject} rules are allowed.")

    return kept


def check_tone(tone: ToneText | None) -> ToneText | None:
    """The desired tone as written, or None when it is blank."""

    return check_optional_text(tone, MAX_TONE_LENGTH, "The tone")


def check_optional_text[OwnerText: str](
    text: OwnerText | None,
    max_length: int,
    subject: str,
) -> OwnerText | None:
    """The text as written, or None when it is missing or blank."""

    if text is None or text.strip() == "":
        return None

    check_text_length(text, max_length, subject)
    return text


def check_text_length(text: str, max_length: int, subject: str) -> None:
    """
    Reject blank texts and texts longer than `max_length` (ignoring spaces
    around them).

    Raises:
        ValidationFailedError: the text is blank or too long.
    """

    length: int = len(text.strip())
    if length == 0:
        raise ValidationFailedError(f"{subject} is empty.")

    if length > max_length:
        raise ValidationFailedError(
            f"{subject} must be at most {max_length} characters."
        )


def validate_links(links: Sequence[BusinessLink]) -> list[BusinessLink]:
    """Links the assistant may send; one link per kind."""

    seen_kinds: set[BusinessLinkKind] = set()
    for link in links:
        if link.kind in seen_kinds:
            raise ValidationFailedError(f"There are two {link.kind} links.")

        seen_kinds.add(link.kind)

    return [link.model_copy() for link in links]
