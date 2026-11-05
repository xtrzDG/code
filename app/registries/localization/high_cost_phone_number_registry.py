import phonenumbers
from phonenumbers import NumberParseException, PhoneNumber, PhoneNumberType

from app.contracts.login_protection import HighCostPhoneNumberRegistryContract
from app.registries.localization.curated_high_cost_phone_ranges import (
    CURATED_HIGH_COST_PHONE_PREFIXES,
)
from app.schemas.typings.localization.booleans import IsHighCostPhoneNumber
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    PhoneNumberPrefix,
)

# Number kinds whose messages cost more than a mobile message, or that
# cannot receive one: a login code to them only serves SMS pumping.
HIGH_COST_NUMBER_TYPES: frozenset[int] = frozenset(
    {
        PhoneNumberType.PREMIUM_RATE,
        PhoneNumberType.SHARED_COST,
        PhoneNumberType.PERSONAL_NUMBER,
        PhoneNumberType.UAN,
        PhoneNumberType.PAGER,
        PhoneNumberType.VOICEMAIL,
    }
)


class HighCostPhoneNumberRegistry(HighCostPhoneNumberRegistryContract):
    """
    Which phone numbers login codes are never sent to: the high-cost kinds
    of libphonenumber's numbering plans (premium rate such as UK 09 and
    French 089, shared cost, personal numbers such as UK 070, universal
    access numbers), the curated satellite and international network
    ranges, and the ranges of OTP_DENIED_PHONE_PREFIXES.
    """

    def __init__(self, denied_prefixes: list[PhoneNumberPrefix]) -> None:
        self._denied_prefixes: tuple[str, ...] = tuple(
            str(prefix)
            for prefix in (*CURATED_HIGH_COST_PHONE_PREFIXES, *denied_prefixes)
        )

    def is_high_cost(self, phone_number: E164PhoneNumber) -> IsHighCostPhoneNumber:
        if str(phone_number).startswith(self._denied_prefixes):
            return True

        try:
            parsed: PhoneNumber = phonenumbers.parse(str(phone_number))
        except NumberParseException:
            return True

        return phonenumbers.number_type(parsed) in HIGH_COST_NUMBER_TYPES
