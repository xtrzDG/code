"""
Which callers a text-back SMS may go to.

The number of a missed call is whatever the calling network presented,
and anyone can spoof it: a burst of calls "from" premium-rate, satellite
or far-away numbers would make the platform pay for SMS that the holder
of the range profits from (SMS pumping). So the SMS leg of a text-back
follows the destination rules of the login codes: never to a high-cost
number (premium rate, shared cost, personal and universal access numbers,
satellite and international networks, the ranges of
OTP_DENIED_PHONE_PREFIXES), never to a line that cannot receive a text (a
landline, a toll-free number), never to a country where sign-up is
restricted, and only to numbers of the business's own country or of an
EU member state, where a local business's callers are. A caller with
another number still gets the WhatsApp text-back, which costs nothing
when it cannot be delivered. The rule is checked when the missed call is
stored and again right before the SMS goes (also after WhatsApp refused
the message).
"""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.login_protection import HighCostPhoneNumberRegistryContract
from app.contracts.registries import CountryRegistryContract
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    PhoneNumberKind,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.channels.transfer_destinations import EU_COUNTRY_CODES

# Lines that cannot receive a text message (as for login codes).
NON_MESSAGING_PHONE_KINDS: frozenset[PhoneNumberKind] = frozenset(
    {PhoneNumberKind.FIXED_LINE, PhoneNumberKind.TOLL_FREE}
)


class TextBackSmsDestinations:
    """Whether a text-back SMS may go to a caller's number (see the module)."""

    def __init__(
        self,
        high_cost_registry: HighCostPhoneNumberRegistryContract,
        country_registry: CountryRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
    ) -> None:
        self._high_cost_registry: HighCostPhoneNumberRegistryContract = (
            high_cost_registry
        )
        self._country_registry: CountryRegistryContract = country_registry
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser

    def allows(self, business: BusinessDocument, caller: E164PhoneNumber) -> bool:
        if self._high_cost_registry.is_high_cost(caller):
            return False

        try:
            details: PhoneNumberDetails = self._phone_number_parser.parse(
                RawPhoneNumberInput(str(caller)), None
            )
        except InvalidPhoneNumberError:
            return False

        if details.kind in NON_MESSAGING_PHONE_KINDS:
            return False

        if (
            details.country_code != business.country_code
            and details.country_code not in EU_COUNTRY_CODES
        ):
            return False

        return (
            self._country_registry.get(details.country_code).onboarding_status
            is not CountryOnboardingStatus.RESTRICTED
        )
